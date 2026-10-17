# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Recipes live in the `justfile` — run `just --list` to see them; this section only covers what isn't obvious from the recipe names.

Almost everything runs through Docker Compose: the app and Postgres come up together, and running tests/migrations outside Docker is **not** the supported path (`just install` and `just lint` are the exceptions — they run on the host). Inside the container, raw commands look like `uv run pytest ...`, `uv run alembic ...`.

- `just test` cycles the DB (downgrade to `base`, upgrade to `head`) before pytest and tears the stack down before and after. Pass pytest args through, e.g. `just test tests/test_decks.py::test_post_decks -x`.
- pytest runs with `--cov=. --cov-report term-missing --cov-fail-under=100` (`pyproject.toml`), so `just test` fails unless tests cover every line of new code.
- `just test-migrations` runs the `pytest-alembic` suite in `tests/migrations/` against an empty database: single head, upgrade, up/down consistency for every revision, and models matching the migrated schema (`alembic check` as a test). `just test` skips that directory (`--ignore` in `addopts`, `omit` in coverage) because it migrates the schema under the transaction-rollback fixture, so the recipe clears `addopts`. CI runs both suites as separate jobs.
- `just migration -m "message"` autogenerates an Alembic revision **against an already-upgraded DB** — the recipe enforces this, so don't run autogen by hand.
- `just lint` runs `eof-fixer`, `ruff format`, `ruff check --fix`, then `ty check`.

Python is 3.14, dependencies managed by `uv`. The API is exposed on `:8000`.

## Architecture

**Stack**: Litestar + SQLAlchemy 2 (async) + advanced-alchemy + Alembic + Postgres + Granian (ASGI server) + modern-di (IoC) + lite-bootstrap (observability/CORS/Sentry/OTel wiring).

**Request flow**: `app/__main__.py` → `granian` → `app.application:build_app` (factory) → `LitestarBootstrapper` from `lite-bootstrap` wraps a `litestar.Litestar` with OpenTelemetry (SQLAlchemy instrumentor), Sentry, CORS, Swagger, etc., based on `Settings.api_bootstrapper_config`.

**Dependency injection** (`app/ioc.py`): `modern_di.Container` is created in `build_app` with `ioc.ALL_GROUPS` and attached via `modern_di_litestar.ModernDIPlugin(di_container, autowired_groups=[ioc.UseCases])`. The plugin registers every `UseCases` provider as a Litestar dependency under its attribute name, so a handler asks for `list_decks_use_case: NamedDependency[ListDecksUseCase]` and nothing is declared in `application.py`. Handlers call the use case and convert the result to a schema; they never touch repositories or the session.

`Database` group:
- `database_engine` — application-scoped primary engine, finalizer disposes the engine
- `database_read_engine` — application-scoped read engine built from `DB_REPLICA_DSN`, or from `DB_DSN` when it is unset. It runs in `AUTOCOMMIT` (no BEGIN/ROLLBACK per request) and sets `default_transaction_read_only=on`, so Postgres rejects writes on it. Each statement sees its own snapshot, so a read that runs several queries can see a write that commits in between. Load related rows in the same query (`fetch_with_cards` uses `joinedload`). Without a replica it is a second pool on the primary, so a process can hold up to `2 × db_pool_size` connections
- `dynamic_engine` — request-scoped; `choose_sa_engine` returns the read engine for `GET`/`HEAD` requests, the primary otherwise (including when there is no request). GET handlers cannot write, and a read right after a write may see replica lag
- `session` — request-scoped, bound to `dynamic_engine`, finalizer closes the session
- `transaction` — request-scoped `db_retry.Transaction` over `session`. Leaving its block rolls back anything uncommitted and closes the session
- `autocommit_transaction` — the same `Transaction`, opened at `AUTOCOMMIT` (`autocommit_isolation_level`). `CreateDeckUseCase` and `UpdateDeckUseCase` use it because each sends exactly one statement, which Postgres runs atomically on its own. The asyncpg adapter then sends no BEGIN or COMMIT, so those writes cost one round trip instead of three. A use case with two or more statements, or one that relies on rolling back after a check, as `UpdateCardsUseCase` does, keeps `transaction`. The `db_session` fixture overrides `autocommit_isolation_level` to `None`, because switching the shared test connection to `AUTOCOMMIT` would roll back its outer transaction. `tests/test_autocommit_writes.py` runs both use cases against a real engine instead, through the `committing_engine` fixture. `tests/test_card_locking.py` uses the same fixture, because a lock wait needs separate connections; both delete the rows they commit.

`Repositories` group (request-scoped): `decks_repository` and `cards_repository`, on `Database.session` with `auto_commit=False`. The use case commits through `transaction.commit()`.

`UseCases` group (request-scoped): one provider per use case in `app/use_cases/`. modern-di fills each dataclass field by its type, so a use case needs no `kwargs`.

**Pool and server sizing**: `DB_POOL_SIZE` (positive) and `DB_MAX_OVERFLOW` (non-negative) size the pool, and `app/__main__.py` sets Granian's `backpressure` to their sum, so each worker accepts only as many requests at once as it has connections. Requests beyond that wait in Granian's socket backlog instead of queueing on the pool. `APP_WORKERS` sets the Granian worker count, and each worker has its own pool. `DB_POOL_TIMEOUT` (default 30 s) bounds the wait for a connection, and a timeout returns 503 through `exceptions.database_unavailable_handler`. advanced-alchemy wraps the timeout in a `RepositoryError`, so the handler is also registered for `RepositoryError` and answers anything not caused by a pool timeout the way Litestar's default handler would: the debug page when `SERVICE_DEBUG` is on, a plain 500 otherwise. `DB_POOL_RECYCLE` defaults to SQLAlchemy's `-1` (never). Set it below the idle timeout of any proxy or load balancer in front of Postgres, so a connection it dropped is not handed out and retried after a 1-2 s backoff.

**Use cases and lost connections**: `pool_pre_ping` is off by default (`DB_POOL_PRE_PING`). A pooled connection that died while idle is handled by `db_retry.postgres_retry` instead, which saves a round trip on every checkout. That only works if the retried function owns its whole transaction, so every use case has this shape:

```python
@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class ListDecksUseCase:
    transaction: Transaction
    decks_repository: DecksRepository

    @postgres_retry
    async def __call__(self, *, after: int | None, limit: int) -> Sequence[models.Deck]:
        async with self.transaction:
            decks: typing.Final = await self.decks_repository.list_decks(after=after, limit=limit)
            await self.transaction.commit()
        return decks
```

- Every query runs inside `async with self.transaction:`. A query before the block leaves the session in a failed transaction on a lost connection, and the retry then fails with `PendingRollbackError`.
- Commit before leaving the block, reads included, and before any early return. Otherwise `__aexit__` rolls back, which expires the loaded rows.
- A retry runs the whole use case again. If the connection drops during `COMMIT`, the write may already have landed. A write that creates rows needs something that makes the second run harmless:
  - `CreateDeckUseCase` takes a client-generated `idempotency_key` (`schemas.DeckCreate`, unique on `decks`). `DecksRepository.get_or_create` sends one `INSERT ... ON CONFLICT (idempotency_key) DO UPDATE SET idempotency_key = EXCLUDED.idempotency_key RETURNING *`. On a conflict the no-op update leaves the row as it was and `RETURNING` hands it back (`DO NOTHING` would return no row), so a retry or a client resend gets the first deck. A concurrent request with the same key waits on the row lock and then gets the same deck. advanced-alchemy's own `upsert` and `get_or_upsert` do a SELECT followed by an INSERT, so they cost two round trips and lose that race.
  - `CreateCardsUseCase` relies on the `(deck_id, front)` unique constraint. A replay is rejected as a duplicate-key error rather than creating the cards twice.
  - Updates (`UpdateDeckUseCase`, `UpdateCardsUseCase`) write the same values again, so a replay is harmless.

**Persistence**: Models inherit `advanced_alchemy.base.BigIntAuditBase` (gives `id: BigInt`, `created_at`, `updated_at`). Metadata is shared with `orm.DeclarativeBase.metadata` in `app/models.py` so Alembic autogen sees everything. Repositories are `SQLAlchemyAsyncRepositoryService[Model]` with a nested `BaseRepository(SQLAlchemyAsyncRepository[Model])`. Use cases call the service methods (`get_many`, `get_one`, `create_many`) for reads and plain inserts. Writes that advanced-alchemy would spread over several round trips are one statement on the session instead: its `update` reads the row twice and refreshes it after the flush, and `upsert_many` selects the rows before and after writing them. `update_deck` sends `UPDATE ... RETURNING` and `get_or_create` sends `INSERT ... ON CONFLICT ... RETURNING`. `update_cards` sends one `WITH locked AS (SELECT id FROM cards WHERE id = ANY(:ids) AND deck_id = :deck_id ORDER BY id FOR UPDATE) UPDATE cards ... FROM unnest(:ids, :fronts, :backs, :hints) AS updates(...), locked WHERE cards.id = updates.id AND cards.id = locked.id AND cards.deck_id = :deck_id RETURNING *`. It binds one array per column, so the SQL text stays the same for any number of cards: SQLAlchemy caches it and asyncpg prepares it once per connection, which a multi-row `VALUES` would not allow. Every updated row must match a `locked` row, and the CTE locks its rows in id order (lazily, one before each update), so concurrent PUTs on overlapping cards always lock them in the same order and cannot deadlock. Without it the lock order follows the plan, which can be the order the client sent; `tests/test_card_locking.py` forces that interleaving. `card_deck_id_front_uc` is `DEFERRABLE INITIALLY IMMEDIATE`, so uniqueness is checked at the end of the statement and one PUT can swap two cards' fronts. It raises `NotFoundError` (404) if fewer rows come back than ids were sent, which rolls the whole request back. PUT never inserts. An `INSERT ... ON CONFLICT (id)` upsert would move a card in from another deck and would insert client-chosen ids without advancing `cards_id_seq`, so a later POST would collide on the primary key. The card handlers cap a request at `schemas.MAX_CARDS_PER_REQUEST` cards, and `update_cards` rejects duplicate ids, both with a 400 before any query runs. Ids in paths, `after` and card bodies are bounded to Postgres `bigint` (`schemas.MAX_ID`), so an oversized id is a 400 and never reaches asyncpg. A POST to a deck that does not exist fails on the foreign key, and `ForeignKeyError` maps to 404. A statement that can hit a unique constraint runs inside `wrap_sqlalchemy_exception` so that it still raises `DuplicateKeyError`. `create_session` in `app/resources/db.py` builds a plain `AsyncSession` with `join_transaction_mode="create_savepoint"`. This is inert in production (the session binds to an engine) but enables the per-test rollback fixture: when a test binds the session to a connection already in a transaction, the session owns its own savepoint so the outer transaction survives commits. Do not "fix" it.

**Test isolation** (`tests/conftest.py`): `db_session` fixture opens a connection, starts a transaction, then **overrides** `Database.dynamic_engine` in the DI container to return that connection. All requests in the test reuse this connection. Each session built against it uses `join_transaction_mode="create_savepoint"`, so `transaction.commit()` releases the session's own savepoint while the outer transaction is rolled back in teardown. DB state is clean between tests with no truncation needed. `app` and `client` fixtures build the real app and run it through `httpx.ASGITransport` + `asgi_lifespan.LifespanManager`. Polyfactory `SQLAlchemyFactory` is wired up via `set_async_session_in_base_sqlalchemy_factory`.

**Migrations**: `migrations/env.py` reads `app.models.METADATA` and rewrites the DSN driver from `postgresql+asyncpg` → `postgresql+psycopg` (Alembic runs on sync psycopg 3). Always run autogen against an upgraded DB — `just migration` enforces this.

**Settings** (`app/settings.py`): `pydantic_settings.BaseSettings` reads from env vars (see `docker-compose.yml` for `SERVICE_DEBUG`, `SERVICE_ENVIRONMENT`, `DB_DSN`; `DB_REPLICA_DSN` is optional). Pool and server sizing uses `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE` and `APP_WORKERS` (see **Pool and server sizing**). `api_bootstrapper_config` builds the `LitestarConfig` consumed by `lite-bootstrap`.

## Conventions

- Routes live in `app/api/`, one module per resource (`decks.py`, `cards.py`), each exposing its own `ROUTER` (`litestar.Router`, prefix `/api`). `application.build_app` registers them all via `route_handlers=[decks.ROUTER, cards.ROUTER]`. Add a new resource by creating `app/api/<name>.py`, defining handlers + a `ROUTER`, and adding it to that list. Its database work goes in `app/use_cases/` with a provider in `ioc.UseCases`.
- Pydantic schemas in `app/schemas.py` use `from_attributes=True` (via `Base`) so they validate directly from ORM instances (`schemas.X.model_validate(orm_instance)`). Collection responses go through `Collection[T].from_models(...)` (e.g. `schemas.Cards`).
- List endpoints page by id (keyset). They take `limit` (1 to `schemas.MAX_PAGE_LIMIT`, default `schemas.DEFAULT_PAGE_LIMIT`) and `after`, the last id the client has seen, and return a `Page[T]` subclass (`schemas.DecksPage`, `schemas.CardsPage`) with `items` and `next_after`. The repository filters `id > after` and fetches `limit + 1` rows ordered by id. `Page.from_models(rows, limit=limit)` drops the extra row and sets `next_after` to the last returned id when that row existed, or `null` on the last page. Don't page with OFFSET: Postgres reads and discards every skipped row.
- Deck responses are deliberately two-shaped: `list_decks`/`create_deck`/`update_deck` return the light `schemas.Deck` (no `cards`), while `get_deck` returns `schemas.DeckWithCards`. The split mirrors loading — lists use `noload` (no cards query), detail uses `joinedload` via `fetch_with_cards` — so the type states exactly what each endpoint loads.
- Domain exceptions: register handlers in `application.build_app`'s `exception_handlers` dict (`DuplicateKeyError` → `exceptions.duplicate_key_error_handler` returns 400, `NotFoundError` and `ForeignKeyError` → `exceptions.not_found_error_handler` returns 404, `sqlalchemy.exc.TimeoutError` and `RepositoryError` → `exceptions.database_unavailable_handler` returns 503 for a pool timeout). Handlers don't raise HTTP errors themselves: a missing row surfaces as advanced-alchemy's `NotFoundError`.
- `ruff` is configured with `select = ["ALL"]` and a line length of 120 — expect strict lint. `app/resources/` is exempt from the `TC` rules because modern-di resolves DI creator annotations at runtime. Type-check with `ty`; suppressions already exist for `invalid-argument-type` around `LifespanManager` / `ASGITransport` in `tests/conftest.py`.

## Agent skills

### Issue tracker

GitHub issues on `modern-python/litestar-sqlalchemy-template`, via `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical roles, each label string equal to its name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

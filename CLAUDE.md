# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All development runs through Docker Compose via `just` (see `Justfile`). The app and Postgres come up together; running tests/migrations outside Docker is not the supported path.

- `just` — full pipeline: install, lint, build, test
- `just run` — start the API (runs `alembic upgrade head` then `python -m app`); exposed on `:8000`
- `just test [pytest-args]` — downgrades DB to `base`, upgrades to `head`, then runs pytest. Wraps with `down` before and after. Pass through args, e.g. `just test tests/test_decks.py::test_create -k pattern -x`
- `just migration -m "message"` — autogenerate an Alembic revision against an up-to-date DB
- `just lint` — `eof-fixer`, `ruff format`, `ruff check --fix`, then `ty check` (this project uses `ty`, not mypy — suppress with `# ty: ignore[<rule>]`)
- `just build` / `just down` / `just sh` — build image / tear down stack / shell into the app container
- `just install` — `uv lock --upgrade` + `uv sync --all-extras --all-groups --frozen`

Python is 3.14, dependencies managed by `uv`. Inside the container, raw commands look like `uv run pytest ...`, `uv run alembic ...`.

## Architecture

**Stack**: Litestar + SQLAlchemy 2 (async) + advanced-alchemy + Alembic + Postgres + Granian (ASGI server) + modern-di (IoC) + lite-bootstrap (observability/CORS/Sentry/OTel wiring).

**Request flow**: `app/__main__.py` → `granian` → `app.application:build_app` (factory) → `LitestarBootstrapper` from `lite-bootstrap` wraps a `litestar.Litestar` with OpenTelemetry (asyncpg + SQLAlchemy instrumentors), Sentry, CORS, Swagger, etc., based on `Settings.api_bootstrapper_config`.

**Dependency injection** (`app/ioc.py`): `modern_di.Container` is created in `build_app` with the `Dependencies` group and attached via `modern_di_litestar.ModernDIPlugin`. Route handlers receive repositories as parameters; `application.py` declares them with `modern_di_litestar.FromDI(...)` so Litestar resolves them per-request. Provider scopes:
- `database_engine` — application-scoped factory, finalizer disposes the engine
- `session` — request-scoped, finalizer closes the session
- `*_repository` — request-scoped, depend on `session`, configured with `auto_commit=True` (advanced-alchemy commits on success / rolls back on exception)

**Persistence**: Models inherit `advanced_alchemy.base.BigIntAuditBase` (gives `id: BigInt`, `created_at`, `updated_at`). Metadata is shared with `orm.DeclarativeBase.metadata` in `app/models.py` so Alembic autogen sees everything. Repositories are `SQLAlchemyAsyncRepositoryService[Model]` with a nested `BaseRepository(SQLAlchemyAsyncRepository[Model])`. Custom `CustomAsyncSession` in `app/resources/db.py` overrides `close()` so test transactions are not actually closed when the session is bound to an `AsyncConnection` — this is what makes the per-test rollback fixture work.

**Test isolation** (`tests/conftest.py`): `db_session` fixture opens a connection, starts a transaction, starts a SAVEPOINT, then **overrides** `Dependencies.database_engine` in the DI container to return that connection. All requests in the test reuse this connection; the outer transaction is rolled back in teardown, so DB state is clean between tests with no truncation needed. `app` and `client` fixtures build the real app and run it through `httpx.ASGITransport` + `asgi_lifespan.LifespanManager`. Polyfactory `SQLAlchemyFactory` is wired up via `set_async_session_in_base_sqlalchemy_factory`.

**Migrations**: `migrations/env.py` reads `app.models.METADATA` and rewrites the DSN driver from `postgresql+asyncpg` → `postgresql` (Alembic uses sync psycopg2). Always run autogen against an upgraded DB — `just migration` enforces this.

**Settings** (`app/settings.py`): `pydantic_settings.BaseSettings` reads from env vars (see `docker-compose.yml` for `SERVICE_DEBUG`, `SERVICE_ENVIRONMENT`, `DB_DSN`). `api_bootstrapper_config` builds the `LitestarConfig` consumed by `lite-bootstrap`.

## Conventions

- Routes live in `app/api/`, registered into a single `ROUTER` (prefix `/api`) referenced from `application.py`. Add a new resource by creating `app/api/<name>.py`, defining handlers + a `Router`, and adding it to `application.build_app`.
- Pydantic schemas in `app/schemas.py` use `from_attributes=True` (via `Base`) so they validate directly from ORM instances (`schemas.X.model_validate(orm_instance)`).
- Domain exceptions: register handlers in `application.build_app`'s `exception_handlers` dict (see `DuplicateKeyError` → `exceptions.duplicate_key_error_handler`). For per-handler 404s the code raises `litestar.exceptions.HTTPException` directly.
- `ruff` is configured with `select = ["ALL"]` and a line length of 120 — expect strict lint. Type-check with `ty`; use `# ty: ignore[<rule>]` for suppressions (already used for `invalid-argument-type` around `LifespanManager` / `ASGITransport` / DTO list construction).

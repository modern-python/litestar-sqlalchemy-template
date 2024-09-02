## Async template on LiteStar and SQLAlchemy 2

[![Test Coverage](https://codecov.io/gh/modern-python/litestar-sqlalchemy-template/branch/main/graph/badge.svg)](https://codecov.io/gh/modern-python/litestar-sqlalchemy-template)
[![GitHub issues](https://img.shields.io/github/issues/modern-python/litestar-sqlalchemy-template)](https://github.com/modern-python/litestar-sqlalchemy-template/issues)
[![GitHub forks](https://img.shields.io/github/forks/modern-python/litestar-sqlalchemy-template)](https://github.com/modern-python/litestar-sqlalchemy-template/network)
[![GitHub stars](https://img.shields.io/github/stars/modern-python/litestar-sqlalchemy-template)](https://github.com/modern-python/litestar-sqlalchemy-template/stargazers)

### Description
Production-ready dockerized async REST API on LiteStar with SQLAlchemy and PostgreSQL

## Key Features
- tests on `pytest` with automatic rollback after each test case
- IOC (Inversion of Control) container built on [that-depends](https://github.com/modern-python/that-depends/) - my DI framework
- Linting and formatting using `ruff` and `mypy`
- `Alembic` for DB migrations

### After `git clone` run
```bash
just --list
```

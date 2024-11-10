import logging
import typing

import modern_di_litestar
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import ioc
from app.application import application


logger = logging.getLogger(__name__)


@pytest.fixture
async def client() -> typing.AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=application),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture(autouse=True)
async def db_session() -> typing.AsyncIterator[AsyncSession]:
    async with modern_di_litestar.fetch_di_container(application) as di_container:
        engine = await ioc.Dependencies.database_engine.async_resolve(di_container)
        connection = await engine.connect()
        transaction = await connection.begin()
        await connection.begin_nested()
        ioc.Dependencies.database_engine.override(connection, di_container)

        try:
            yield AsyncSession(connection, expire_on_commit=False, autoflush=False)
        finally:
            if connection.in_transaction():
                await transaction.rollback()
            await connection.close()
            await engine.dispose()
            logger.info("Fixture db_session is closed")

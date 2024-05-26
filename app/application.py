import contextlib
import typing

import litestar

from app import exceptions, ioc
from app.api.decks import ROUTER
from app.exceptions import DatabaseValidationError


class AppBuilder:
    def __init__(self) -> None:
        self.settings = ioc.IOCContainer.settings.sync_resolve()
        self.app: litestar.Litestar = litestar.Litestar(
            debug=self.settings.debug,
            lifespan=[self.lifespan_manager],
            exception_handlers={DatabaseValidationError: exceptions.database_validation_exception_handler},
            route_handlers=[ROUTER],
        )

    @contextlib.asynccontextmanager
    async def lifespan_manager(self, _: litestar.Litestar | None) -> typing.AsyncIterator[None]:
        try:
            await ioc.IOCContainer.init_async_resources()
            yield
        finally:
            await ioc.IOCContainer.tear_down()


application = AppBuilder().app

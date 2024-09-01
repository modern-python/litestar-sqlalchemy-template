import contextlib
import typing

import litestar
from advanced_alchemy.exceptions import ForeignKeyError

from app import exceptions, ioc
from app.api.decks import ROUTER


class AppBuilder:
    def __init__(self) -> None:
        self.settings = ioc.IOCContainer.settings.sync_resolve()
        self.app: litestar.Litestar = litestar.Litestar(
            debug=self.settings.debug,
            lifespan=[self.lifespan_manager],
            exception_handlers={ForeignKeyError: exceptions.foreign_key_error_handler},
            route_handlers=[ROUTER],
        )

    @contextlib.asynccontextmanager
    async def lifespan_manager(self, _: litestar.Litestar | None) -> typing.AsyncIterator[None]:
        try:
            await ioc.IOCContainer.init_resources()
            yield
        finally:
            await ioc.IOCContainer.tear_down()


application = AppBuilder().app

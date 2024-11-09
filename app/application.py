import contextlib
import typing

import litestar
import modern_di
import modern_di_litestar
from advanced_alchemy.exceptions import DuplicateKeyError
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin

from app import exceptions, ioc
from app.api.decks import ROUTER
from app.settings import settings


class AppBuilder:
    def __init__(self) -> None:
        self.app: litestar.Litestar = litestar.Litestar(
            debug=settings.debug,
            lifespan=[self.lifespan_manager],
            exception_handlers={
                DuplicateKeyError: exceptions.duplicate_key_error_handler,
            },
            route_handlers=[ROUTER],
            dependencies={
                **modern_di_litestar.prepare_di_dependencies(),
                "decks_service": modern_di_litestar.FromDI(ioc.Dependencies.decks_service),
                "cards_service": modern_di_litestar.FromDI(ioc.Dependencies.cards_service),
            },
            openapi_config=OpenAPIConfig(
                title="Litestar Example",
                description="Example of Litestar with Scalar OpenAPI docs",
                version="0.0.1",
                render_plugins=[SwaggerRenderPlugin()],
            ),
        )
        self.di_container = modern_di.Container(scope=modern_di.Scope.APP)
        self.app.state.di_container = self.di_container

    @contextlib.asynccontextmanager
    async def lifespan_manager(self, _: litestar.Litestar | None) -> typing.AsyncIterator[None]:
        async with self.di_container:
            await ioc.Dependencies.async_resolve_creators(self.di_container)
            yield


application = AppBuilder().app

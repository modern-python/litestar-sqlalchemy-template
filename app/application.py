import litestar
import modern_di_litestar
from advanced_alchemy.exceptions import DuplicateKeyError
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin

from app import exceptions, ioc
from app.api.decks import ROUTER
from app.settings import settings


def build_app() -> litestar.Litestar:
    return litestar.Litestar(
        debug=settings.debug,
        exception_handlers={
            DuplicateKeyError: exceptions.duplicate_key_error_handler,
        },
        route_handlers=[ROUTER],
        plugins=[modern_di_litestar.ModernDIPlugin()],
        dependencies={
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


application = build_app()

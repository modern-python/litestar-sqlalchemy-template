import dataclasses

import litestar
import modern_di
import modern_di_litestar
from advanced_alchemy.exceptions import DuplicateKeyError
from lite_bootstrap import LitestarBootstrapper
from litestar.config.app import AppConfig
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from app import exceptions, ioc, repositories
from app.api.decks import ROUTER
from app.settings import settings


def build_app() -> litestar.Litestar:
    di_container = modern_di.AsyncContainer(groups=[ioc.Dependencies])
    bootstrap_config = dataclasses.replace(
        settings.api_bootstrapper_config,
        application_config=AppConfig(
            exception_handlers={
                DuplicateKeyError: exceptions.duplicate_key_error_handler,
            },
            route_handlers=[ROUTER],
            plugins=[modern_di_litestar.ModernDIPlugin(di_container)],
            dependencies={
                "decks_service": modern_di_litestar.FromDI(repositories.DecksService),
                "cards_service": modern_di_litestar.FromDI(repositories.CardsService),
            },
            request_max_body_size=settings.request_max_body_size,
        ),
        opentelemetry_instrumentors=[
            SQLAlchemyInstrumentor(),
            AsyncPGInstrumentor(capture_parameters=True),  # type: ignore[no-untyped-call]
        ],
    )
    bootstrapper = LitestarBootstrapper(bootstrap_config=bootstrap_config)
    return bootstrapper.bootstrap()

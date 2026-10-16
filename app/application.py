import dataclasses
from typing import TYPE_CHECKING

import modern_di
import modern_di_litestar
from advanced_alchemy.exceptions import DuplicateKeyError, NotFoundError
from lite_bootstrap import LitestarBootstrapper
from litestar.config.app import AppConfig
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from app import exceptions, ioc
from app.api import cards, decks
from app.settings import settings


if TYPE_CHECKING:
    import litestar


def build_app() -> litestar.Litestar:
    di_container = modern_di.Container(groups=ioc.ALL_GROUPS)
    bootstrap_config = dataclasses.replace(
        settings.api_bootstrapper_config,
        application_config=AppConfig(
            exception_handlers={
                DuplicateKeyError: exceptions.duplicate_key_error_handler,
                NotFoundError: exceptions.not_found_error_handler,
            },
            route_handlers=[decks.ROUTER, cards.ROUTER],
            plugins=[modern_di_litestar.ModernDIPlugin(di_container, autowired_groups=[ioc.UseCases])],
            request_max_body_size=settings.request_max_body_size,
        ),
        opentelemetry_instrumentors=[SQLAlchemyInstrumentor()],
    )
    bootstrapper = LitestarBootstrapper(bootstrap_config=bootstrap_config)
    return bootstrapper.bootstrap()

from starlite import Starlite
from starlite.exceptions import ValidationException

from app.apps.decks.views import decks_router
from app.config import settings
from app.db.exceptions import DatabaseValidationError
from app.db.middleware import SQLAlchemySessionMiddleware
from app.exceptions import database_validation_exception_handler, request_validation_exception_handler


app = Starlite(
    route_handlers=[decks_router],
    debug=settings.DEBUG,
    middleware=[] if settings.IS_TESTING else [SQLAlchemySessionMiddleware],
    exception_handlers={
        DatabaseValidationError: database_validation_exception_handler,  # type: ignore
        ValidationException: request_validation_exception_handler,  # type: ignore
    },
)

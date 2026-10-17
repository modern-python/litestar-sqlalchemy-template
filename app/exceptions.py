import typing

import litestar
from litestar import status_codes
from litestar.exceptions.responses import create_debug_response, create_exception_response
from sqlalchemy import exc as sa_exc


if typing.TYPE_CHECKING:
    from advanced_alchemy.exceptions import DuplicateKeyError, ForeignKeyError, NotFoundError


def duplicate_key_error_handler(_: object, exc: DuplicateKeyError) -> litestar.Response[dict[str, typing.Any]]:
    return litestar.Response(
        media_type=litestar.MediaType.JSON,
        content={"detail": exc.detail},
        status_code=status_codes.HTTP_400_BAD_REQUEST,
    )


def not_found_error_handler(_: object, __: NotFoundError | ForeignKeyError) -> litestar.Response[dict[str, typing.Any]]:
    return litestar.Response(
        media_type=litestar.MediaType.JSON,
        content={"detail": "Not found"},
        status_code=status_codes.HTTP_404_NOT_FOUND,
    )


def database_unavailable_handler(request: litestar.Request, exc: Exception) -> litestar.Response[typing.Any]:
    if not isinstance(exc, sa_exc.TimeoutError) and not isinstance(exc.__cause__, sa_exc.TimeoutError):
        fallback: typing.Final = create_debug_response if request.app.debug else create_exception_response
        return fallback(request=request, exc=exc)
    return litestar.Response(
        media_type=litestar.MediaType.JSON,
        content={"detail": "Database unavailable"},
        status_code=status_codes.HTTP_503_SERVICE_UNAVAILABLE,
    )

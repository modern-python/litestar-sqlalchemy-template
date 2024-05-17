import typing

import litestar
from litestar import status_codes


class DatabaseError(Exception):
    pass


class DatabaseValidationError(DatabaseError):
    def __init__(self, message: str, field: str | None = None) -> None:
        self.message = message
        self.field = field


def database_validation_exception_handler(
    _: object, exc: DatabaseValidationError
) -> litestar.Response[dict[str, typing.Any]]:
    return litestar.Response(
        media_type=litestar.MediaType.JSON,
        content={
            "detail": "Database validation failed",
            "extra": [{"message": exc.message, "key": exc.field or "__root__"}],
        },
        status_code=status_codes.HTTP_400_BAD_REQUEST,
    )

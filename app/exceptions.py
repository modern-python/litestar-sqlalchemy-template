import typing

import litestar
from advanced_alchemy.exceptions import ForeignKeyError
from litestar import status_codes


def database_validation_exception_handler(_: object, exc: ForeignKeyError) -> litestar.Response[dict[str, typing.Any]]:
    return litestar.Response(
        media_type=litestar.MediaType.JSON,
        content={
            "detail": "Database validation failed",
            "extra": [{"message": exc.detail, "key": "__root__"}],
        },
        status_code=status_codes.HTTP_400_BAD_REQUEST,
    )

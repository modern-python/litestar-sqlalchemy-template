import typing

import litestar
from advanced_alchemy.exceptions import ForeignKeyError
from litestar import status_codes


def foreign_key_error_handler(_: object, exc: ForeignKeyError) -> litestar.Response[dict[str, typing.Any]]:
    return litestar.Response(
        media_type=litestar.MediaType.JSON,
        content={"detail": exc.detail},
        status_code=status_codes.HTTP_400_BAD_REQUEST,
    )

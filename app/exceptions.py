import typing

import litestar
from advanced_alchemy.exceptions import DuplicateKeyError
from litestar import status_codes


def duplicate_key_error_handler(_: object, exc: DuplicateKeyError) -> litestar.Response[dict[str, typing.Any]]:
    return litestar.Response(
        media_type=litestar.MediaType.JSON,
        content={"detail": exc.detail},
        status_code=status_codes.HTTP_400_BAD_REQUEST,
    )

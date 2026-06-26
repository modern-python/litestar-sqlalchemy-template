import typing

import litestar
from litestar import status_codes


if typing.TYPE_CHECKING:
    from advanced_alchemy.exceptions import DuplicateKeyError, NotFoundError


def duplicate_key_error_handler(_: object, exc: DuplicateKeyError) -> litestar.Response[dict[str, typing.Any]]:
    return litestar.Response(
        media_type=litestar.MediaType.JSON,
        content={"detail": exc.detail},
        status_code=status_codes.HTTP_400_BAD_REQUEST,
    )


def not_found_error_handler(_: object, __: NotFoundError) -> litestar.Response[dict[str, typing.Any]]:
    return litestar.Response(
        media_type=litestar.MediaType.JSON,
        content={"detail": "Not found"},
        status_code=status_codes.HTTP_404_NOT_FOUND,
    )

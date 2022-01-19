from typing import Any, Sequence, Type, cast

from pydantic import BaseModel, create_model
from pydantic.error_wrappers import ErrorList, ErrorWrapper, ValidationError
from starlette import status
from starlite import MediaType, Request, Response
from starlite.exceptions import ValidationException

from app.db.exceptions import DatabaseValidationError


RequestErrorModel: Type[BaseModel] = create_model("Request")


class RequestValidationError(ValidationError):
    def __init__(self, errors: Sequence[ErrorList], *, body: Any = None) -> None:
        self.body = body
        super().__init__(errors, RequestErrorModel)


async def request_validation_exception_handler(_: Request, exc: ValidationException) -> Response:
    cause = cast(RequestValidationError, exc.__cause__)
    return Response(
        media_type=MediaType.JSON,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": cause.errors()},
    )


def database_validation_exception_handler(_: Request, exc: DatabaseValidationError) -> Response:
    exc_ = RequestValidationError([ErrorWrapper(ValueError(exc.message), loc=exc.field or "__root__")])
    return Response(
        media_type=MediaType.JSON,
        content={"detail": exc_.errors()},
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )

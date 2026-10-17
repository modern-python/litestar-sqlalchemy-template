from typing import Annotated

from litestar.params import PathParameter

from app import schemas


PathId = Annotated[int, PathParameter(gt=0, le=schemas.MAX_ID)]

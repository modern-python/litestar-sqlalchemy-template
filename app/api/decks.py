import typing
from typing import Annotated

import litestar
from litestar.di import NamedDependency
from litestar.params import QueryParameter

from app import schemas
from app.api import PathId
from app.use_cases.create_deck import CreateDeckUseCase
from app.use_cases.get_deck import GetDeckUseCase
from app.use_cases.list_decks import ListDecksUseCase
from app.use_cases.update_deck import UpdateDeckUseCase


@litestar.get("/decks/")
async def list_decks(
    list_decks_use_case: NamedDependency[ListDecksUseCase],
    after: Annotated[int | None, QueryParameter(gt=0, le=schemas.MAX_ID)] = None,
    limit: Annotated[int, QueryParameter(ge=1, le=schemas.MAX_PAGE_LIMIT)] = schemas.DEFAULT_PAGE_LIMIT,
) -> schemas.DecksPage:
    decks: typing.Final = await list_decks_use_case(after=after, limit=limit)
    return schemas.DecksPage.from_models(decks, limit=limit)


@litestar.get("/decks/{deck_id:int}/")
async def get_deck(deck_id: PathId, get_deck_use_case: NamedDependency[GetDeckUseCase]) -> schemas.DeckWithCards:
    return schemas.DeckWithCards.model_validate(await get_deck_use_case(deck_id=deck_id))


@litestar.put("/decks/{deck_id:int}/")
async def update_deck(
    deck_id: PathId,
    data: schemas.DeckUpdate,
    update_deck_use_case: NamedDependency[UpdateDeckUseCase],
) -> schemas.Deck:
    return schemas.Deck.model_validate(await update_deck_use_case(deck_id=deck_id, data=data))


@litestar.post("/decks/")
async def create_deck(
    data: schemas.DeckCreate, create_deck_use_case: NamedDependency[CreateDeckUseCase]
) -> schemas.Deck:
    return schemas.Deck.model_validate(await create_deck_use_case(data=data))


ROUTER: typing.Final = litestar.Router(
    path="/api",
    route_handlers=[list_decks, get_deck, update_deck, create_deck],
)

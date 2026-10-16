import typing

import litestar
from litestar.di import NamedDependency
from litestar.params import FromPath

from app import schemas
from app.use_cases.create_deck import CreateDeckUseCase
from app.use_cases.get_deck import GetDeckUseCase
from app.use_cases.list_decks import ListDecksUseCase
from app.use_cases.update_deck import UpdateDeckUseCase


@litestar.get("/decks/")
async def list_decks(list_decks_use_case: NamedDependency[ListDecksUseCase]) -> schemas.Decks:
    return schemas.Decks.from_models(await list_decks_use_case())


@litestar.get("/decks/{deck_id:int}/")
async def get_deck(deck_id: FromPath[int], get_deck_use_case: NamedDependency[GetDeckUseCase]) -> schemas.DeckWithCards:
    return schemas.DeckWithCards.model_validate(await get_deck_use_case(deck_id=deck_id))


@litestar.put("/decks/{deck_id:int}/")
async def update_deck(
    deck_id: FromPath[int],
    data: schemas.DeckCreate,
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

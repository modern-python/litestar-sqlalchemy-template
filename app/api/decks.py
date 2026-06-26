import typing

import litestar
from litestar.params import FromPath  # noqa: TC002

from app import schemas
from app.repositories import DecksRepository  # noqa: TC001


@litestar.get("/decks/")
async def list_decks(decks_repository: DecksRepository) -> schemas.Decks:
    objects = await decks_repository.get_many()
    return schemas.Decks.from_models(objects)


@litestar.get("/decks/{deck_id:int}/")
async def get_deck(deck_id: FromPath[int], decks_repository: DecksRepository) -> schemas.DeckWithCards:
    instance = await decks_repository.fetch_with_cards(deck_id)
    return schemas.DeckWithCards.model_validate(instance)


@litestar.put("/decks/{deck_id:int}/")
async def update_deck(
    deck_id: FromPath[int],
    data: schemas.DeckCreate,
    decks_repository: DecksRepository,
) -> schemas.Deck:
    instance = await decks_repository.update(data=data.model_dump(), item_id=deck_id)
    return schemas.Deck.model_validate(instance)


@litestar.post("/decks/")
async def create_deck(data: schemas.DeckCreate, decks_repository: DecksRepository) -> schemas.Deck:
    instance = await decks_repository.create(data)
    return schemas.Deck.model_validate(instance)


ROUTER: typing.Final = litestar.Router(
    path="/api",
    route_handlers=[list_decks, get_deck, update_deck, create_deck],
)

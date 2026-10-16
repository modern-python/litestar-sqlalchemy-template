import typing

import litestar
from db_retry import Transaction, postgres_retry
from litestar.di import NamedDependency
from litestar.params import FromPath

from app import schemas
from app.repositories import DecksRepository


@litestar.get("/decks/")
@postgres_retry
async def list_decks(
    decks_repository: NamedDependency[DecksRepository], transaction: NamedDependency[Transaction]
) -> schemas.Decks:
    async with transaction:
        objects = await decks_repository.get_many()
        await transaction.commit()
    return schemas.Decks.from_models(objects)


@litestar.get("/decks/{deck_id:int}/")
@postgres_retry
async def get_deck(
    deck_id: FromPath[int],
    decks_repository: NamedDependency[DecksRepository],
    transaction: NamedDependency[Transaction],
) -> schemas.DeckWithCards:
    async with transaction:
        instance = await decks_repository.fetch_with_cards(deck_id)
        await transaction.commit()
    return schemas.DeckWithCards.model_validate(instance)


@litestar.put("/decks/{deck_id:int}/")
@postgres_retry
async def update_deck(
    deck_id: FromPath[int],
    data: schemas.DeckCreate,
    decks_repository: NamedDependency[DecksRepository],
    transaction: NamedDependency[Transaction],
) -> schemas.Deck:
    async with transaction:
        instance = await decks_repository.update(data=data.model_dump(), item_id=deck_id)
        await transaction.commit()
    return schemas.Deck.model_validate(instance)


@litestar.post("/decks/")
@postgres_retry
async def create_deck(
    data: schemas.DeckCreate,
    decks_repository: NamedDependency[DecksRepository],
    transaction: NamedDependency[Transaction],
) -> schemas.Deck:
    async with transaction:
        instance = await decks_repository.create(data)
        await transaction.commit()
    return schemas.Deck.model_validate(instance)


ROUTER: typing.Final = litestar.Router(
    path="/api",
    route_handlers=[list_decks, get_deck, update_deck, create_deck],
)

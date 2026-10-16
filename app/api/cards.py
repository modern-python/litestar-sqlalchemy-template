import typing

import litestar
from db_retry import Transaction, postgres_retry
from litestar.di import NamedDependency
from litestar.params import FromPath

from app import models, schemas
from app.repositories import CardsRepository


@litestar.get("/decks/{deck_id:int}/cards/")
@postgres_retry
async def list_cards(
    deck_id: FromPath[int],
    cards_repository: NamedDependency[CardsRepository],
    transaction: NamedDependency[Transaction],
) -> schemas.Cards:
    async with transaction:
        objects = await cards_repository.list_for_deck(deck_id)
        await transaction.commit()
    return schemas.Cards.from_models(objects)


@litestar.get("/cards/{card_id:int}/")
@postgres_retry
async def get_card(
    card_id: FromPath[int],
    cards_repository: NamedDependency[CardsRepository],
    transaction: NamedDependency[Transaction],
) -> schemas.Card:
    async with transaction:
        instance = await cards_repository.get_one(models.Card.id == card_id)
        await transaction.commit()
    return schemas.Card.model_validate(instance)


@litestar.post("/decks/{deck_id:int}/cards/")
@postgres_retry
async def create_cards(
    deck_id: FromPath[int],
    data: list[schemas.CardCreate],
    cards_repository: NamedDependency[CardsRepository],
    transaction: NamedDependency[Transaction],
) -> schemas.Cards:
    async with transaction:
        objects = await cards_repository.add_cards(deck_id, data)
        await transaction.commit()
    return schemas.Cards.from_models(objects)


@litestar.put("/decks/{deck_id:int}/cards/")
@postgres_retry
async def update_cards(
    deck_id: FromPath[int],
    data: list[schemas.Card],
    cards_repository: NamedDependency[CardsRepository],
    transaction: NamedDependency[Transaction],
) -> schemas.Cards:
    async with transaction:
        objects = await cards_repository.upsert_cards(deck_id, data)
        await transaction.commit()
    return schemas.Cards.from_models(objects)


ROUTER: typing.Final = litestar.Router(
    path="/api",
    route_handlers=[list_cards, get_card, create_cards, update_cards],
)

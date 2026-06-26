import typing

import litestar
from litestar.params import FromPath  # noqa: TC002

from app import models, schemas
from app.repositories import CardsRepository, DecksRepository  # noqa: TC001


@litestar.get("/decks/")
async def list_decks(decks_repository: DecksRepository) -> schemas.Decks:
    objects = await decks_repository.get_many()
    return schemas.Decks.from_models(objects)


@litestar.get("/decks/{deck_id:int}/")
async def get_deck(deck_id: FromPath[int], decks_repository: DecksRepository) -> schemas.Deck:
    instance = await decks_repository.fetch_with_cards(deck_id)
    return schemas.Deck.model_validate(instance)


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


@litestar.get("/decks/{deck_id:int}/cards/")
async def list_cards(deck_id: FromPath[int], cards_repository: CardsRepository) -> schemas.Cards:
    objects = await cards_repository.list_for_deck(deck_id)
    return schemas.Cards.from_models(objects)


@litestar.get("/cards/{card_id:int}/")
async def get_card(card_id: FromPath[int], cards_repository: CardsRepository) -> schemas.Card:
    instance = await cards_repository.get_one(models.Card.id == card_id)
    return schemas.Card.model_validate(instance)


@litestar.post("/decks/{deck_id:int}/cards/")
async def create_cards(
    deck_id: FromPath[int], data: list[schemas.CardCreate], cards_repository: CardsRepository
) -> schemas.Cards:
    objects = await cards_repository.add_cards(deck_id, data)
    return schemas.Cards.from_models(objects)


@litestar.put("/decks/{deck_id:int}/cards/")
async def update_cards(
    deck_id: FromPath[int], data: list[schemas.Card], cards_repository: CardsRepository
) -> schemas.Cards:
    objects = await cards_repository.upsert_cards(deck_id, data)
    return schemas.Cards.from_models(objects)


ROUTER: typing.Final = litestar.Router(
    path="/api",
    route_handlers=[list_decks, get_deck, update_deck, create_deck, list_cards, get_card, create_cards, update_cards],
)

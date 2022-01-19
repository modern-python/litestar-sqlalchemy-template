from typing import List

from starlite import Router
from starlite.controller import Controller
from starlite.exceptions import NotFoundException
from starlite.handlers import get, patch, post

from app.apps.decks import models, schemas
from app.db.utils import transaction


class DeckController(Controller):
    path = "/decks"

    @get()
    async def list_decks(self) -> schemas.Decks:
        objects = await models.Deck.all()
        return schemas.Decks.parse_obj({"items": objects})

    @get(path="/{deck_id:int}")
    async def get_deck(self, deck_id: int) -> schemas.Deck:
        instance = await models.Deck.get_by_id(deck_id, prefetch=("cards",))
        if not instance:
            raise NotFoundException(detail="Deck is not found")
        return schemas.Deck.from_orm(instance)

    @patch(path="/{deck_id:int}")
    async def update_deck(self, deck_id: int, data: schemas.DeckCreate) -> schemas.Deck:
        instance = await models.Deck.get_by_id(deck_id)
        if not instance:
            raise NotFoundException(detail="Deck is not found")
        await instance.update_attrs(**data.dict())
        await instance.save()
        return schemas.Deck.from_orm(instance)

    @post()
    async def create_deck(self, data: schemas.DeckCreate) -> schemas.Deck:
        instance = models.Deck(**data.dict())
        await instance.save()
        return schemas.Deck.from_orm(instance)

    @get(path="/{deck_id:int}/cards/")
    async def list_cards(self, deck_id: int) -> schemas.Cards:
        objects = await models.Card.filter({"deck_id": deck_id})
        return schemas.Cards.parse_obj({"items": objects})

    @post(path="/{deck_id:int}/cards/")
    async def create_cards(self, deck_id: int, data: List[schemas.CardCreate]) -> schemas.Cards:
        async with transaction():
            objects = await models.Card.bulk_create(
                [models.Card(**card.dict(), deck_id=deck_id) for card in data],
            )
        return schemas.Cards.parse_obj({"items": objects})

    @patch(path="/{deck_id:int}/cards/")
    async def update_cards(self, deck_id: int, data: List[schemas.Card]) -> schemas.Cards:
        async with transaction():
            objects = await models.Card.bulk_update(
                [models.Card(**card.dict(exclude={"deck_id"}), deck_id=deck_id) for card in data],
            )
        return schemas.Cards.parse_obj({"items": objects})


@get(path="/cards/{card_id:int}/")
async def get_card(card_id: int) -> schemas.Card:
    instance = await models.Card.get_by_id(card_id)
    if not instance:
        raise NotFoundException(detail="Card is not found")
    return schemas.Card.from_orm(instance)


decks_router = Router(path="/api", route_handlers=[DeckController, get_card])

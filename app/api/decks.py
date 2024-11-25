import typing

import litestar
from advanced_alchemy.exceptions import NotFoundError
from litestar import status_codes
from litestar.exceptions import HTTPException
from litestar.plugins.pydantic import PydanticDTO
from sqlalchemy import orm

from app import models, schemas
from app.repositories import CardsService, DecksService


@litestar.get("/decks/")
async def list_decks(decks_service: DecksService) -> schemas.Decks:
    objects = await decks_service.list()
    return schemas.Decks(items=objects)  # type: ignore[arg-type]


@litestar.get("/decks/{deck_id:int}/")
async def get_deck(deck_id: int, decks_service: DecksService) -> schemas.Deck:
    instance = await decks_service.get_one_or_none(
        models.Deck.id == deck_id,
        load=[orm.selectinload(models.Deck.cards)],
    )
    if not instance:
        raise HTTPException(status_code=status_codes.HTTP_404_NOT_FOUND, detail="Deck is not found")

    return schemas.Deck.model_validate(instance)


@litestar.put("/decks/{deck_id:int}/")
async def update_deck(
    deck_id: int,
    data: schemas.DeckCreate,
    decks_service: DecksService,
) -> schemas.Deck:
    try:
        instance = await decks_service.update(data=data.model_dump(), item_id=deck_id)
    except NotFoundError:
        raise HTTPException(status_code=status_codes.HTTP_404_NOT_FOUND, detail="Deck is not found") from None
    return schemas.Deck.model_validate(instance)


@litestar.post("/decks/")
async def create_deck(data: schemas.DeckCreate, decks_service: DecksService) -> schemas.Deck:
    instance = await decks_service.create(data)
    return schemas.Deck.model_validate(instance)


@litestar.get("/decks/{deck_id:int}/cards/")
async def list_cards(deck_id: int, cards_service: CardsService) -> schemas.Cards:
    objects = await cards_service.list(models.Card.deck_id == deck_id)
    return schemas.Cards(items=objects)  # type: ignore[arg-type]


@litestar.get("/cards/{card_id:int}/", return_dto=PydanticDTO[schemas.Card])
async def get_card(card_id: int, cards_service: CardsService) -> schemas.Card:
    instance = await cards_service.get_one_or_none(models.Card.id == card_id)
    if not instance:
        raise HTTPException(status_code=status_codes.HTTP_404_NOT_FOUND, detail="Card is not found")
    return schemas.Card.model_validate(instance)


@litestar.post("/decks/{deck_id:int}/cards/")
async def create_cards(deck_id: int, data: list[schemas.CardCreate], cards_service: CardsService) -> schemas.Cards:
    objects = await cards_service.create_many(
        data=[models.Card(**card.model_dump(), deck_id=deck_id) for card in data],
    )
    return schemas.Cards(items=objects)  # type: ignore[arg-type]


@litestar.put("/decks/{deck_id:int}/cards/")
async def update_cards(deck_id: int, data: list[schemas.Card], cards_service: CardsService) -> schemas.Cards:
    objects = await cards_service.upsert_many(
        data=[models.Card(**card.model_dump(exclude={"deck_id"}), deck_id=deck_id) for card in data],
    )
    return schemas.Cards(items=objects)  # type: ignore[arg-type]


ROUTER: typing.Final = litestar.Router(
    path="/api",
    route_handlers=[list_decks, get_deck, update_deck, create_deck, list_cards, get_card, create_cards, update_cards],
)

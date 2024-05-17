import typing

import litestar
from litestar import status_codes
from litestar.contrib.pydantic import PydanticDTO
from litestar.exceptions import HTTPException
from that_depends.providers import container_context

from app import ioc, models, schemas


@litestar.get("/decks/")
@container_context()
async def list_decks() -> schemas.Decks:
    decks_repo = await ioc.IOCContainer.decks_repo()
    objects = await decks_repo.all()
    return schemas.Decks(items=objects)  # type: ignore[arg-type]


@litestar.get("/decks/{deck_id:int}/")
@container_context()
async def get_deck(deck_id: int) -> schemas.Deck:
    decks_repo = await ioc.IOCContainer.decks_repo()
    instance = await decks_repo.get_by_id(deck_id, prefetch=("cards",))
    if not instance:
        raise HTTPException(status_code=status_codes.HTTP_404_NOT_FOUND, detail="Deck is not found")

    return schemas.Deck.model_validate(instance)


@litestar.put("/decks/{deck_id:int}/")
@container_context()
async def update_deck(
    deck_id: int,
    data: schemas.DeckCreate,
) -> schemas.Deck:
    decks_repo = await ioc.IOCContainer.decks_repo()
    instance = await decks_repo.get_by_id(deck_id)
    if not instance:
        raise HTTPException(status_code=status_codes.HTTP_404_NOT_FOUND, detail="Deck is not found")

    await decks_repo.update_attrs(instance, **data.model_dump())
    await decks_repo.save(instance)
    return schemas.Deck.model_validate(instance)


@litestar.post("/decks/")
@container_context()
async def create_deck(data: schemas.DeckCreate) -> schemas.Deck:
    decks_repo = await ioc.IOCContainer.decks_repo()
    instance = models.Deck(**data.model_dump())
    await decks_repo.save(instance)
    return schemas.Deck.model_validate(instance)


@litestar.get("/decks/{deck_id:int}/cards/")
@container_context()
async def list_cards(deck_id: int) -> schemas.Cards:
    cards_repo = await ioc.IOCContainer.cards_repo()
    objects = await cards_repo.filter({"deck_id": deck_id})
    return schemas.Cards(items=objects)  # type: ignore[arg-type]


@litestar.get("/cards/{card_id:int}/", return_dto=PydanticDTO[schemas.Card])
@container_context()
async def get_card(card_id: int) -> schemas.Card:
    cards_repo = await ioc.IOCContainer.cards_repo()
    instance = await cards_repo.get_by_id(card_id)
    if not instance:
        raise HTTPException(status_code=status_codes.HTTP_404_NOT_FOUND, detail="Card is not found")
    return schemas.Card.model_validate(instance)


@litestar.post("/decks/{deck_id:int}/cards/")
@container_context()
async def create_cards(
    deck_id: int,
    data: list[schemas.CardCreate],
) -> schemas.Cards:
    cards_repo = await ioc.IOCContainer.cards_repo()
    objects = await cards_repo.bulk_create(
        [models.Card(**card.model_dump(), deck_id=deck_id) for card in data],
    )
    return schemas.Cards(items=objects)  # type: ignore[arg-type]


@litestar.put("/decks/{deck_id:int}/cards/")
@container_context()
async def update_cards(
    deck_id: int,
    data: list[schemas.Card],
) -> schemas.Cards:
    cards_repo = await ioc.IOCContainer.cards_repo()
    objects = await cards_repo.bulk_update(
        [models.Card(**card.model_dump(exclude={"deck_id"}), deck_id=deck_id) for card in data],
    )
    return schemas.Cards(items=objects)  # type: ignore[arg-type]


ROUTER: typing.Final = litestar.Router(
    path="/api",
    route_handlers=[list_decks, get_deck, update_deck, create_deck, list_cards, get_card, create_cards, update_cards],
)

import typing
from typing import Annotated

import litestar
from litestar.di import NamedDependency
from litestar.params import FromPath, QueryParameter

from app import schemas
from app.use_cases.create_cards import CreateCardsUseCase
from app.use_cases.get_card import GetCardUseCase
from app.use_cases.list_cards import ListCardsUseCase
from app.use_cases.update_cards import UpdateCardsUseCase


@litestar.get("/decks/{deck_id:int}/cards/")
async def list_cards(
    deck_id: FromPath[int],
    list_cards_use_case: NamedDependency[ListCardsUseCase],
    after: Annotated[int | None, QueryParameter(gt=0)] = None,
    limit: Annotated[int, QueryParameter(ge=1, le=schemas.MAX_PAGE_LIMIT)] = schemas.DEFAULT_PAGE_LIMIT,
) -> schemas.CardsPage:
    cards: typing.Final = await list_cards_use_case(deck_id=deck_id, after=after, limit=limit)
    return schemas.CardsPage.from_models(cards, limit=limit)


@litestar.get("/cards/{card_id:int}/")
async def get_card(card_id: FromPath[int], get_card_use_case: NamedDependency[GetCardUseCase]) -> schemas.Card:
    return schemas.Card.model_validate(await get_card_use_case(card_id=card_id))


@litestar.post("/decks/{deck_id:int}/cards/")
async def create_cards(
    deck_id: FromPath[int],
    data: list[schemas.CardCreate],
    create_cards_use_case: NamedDependency[CreateCardsUseCase],
) -> schemas.Cards:
    return schemas.Cards.from_models(await create_cards_use_case(deck_id=deck_id, data=data))


@litestar.put("/decks/{deck_id:int}/cards/")
async def update_cards(
    deck_id: FromPath[int],
    data: list[schemas.CardUpdate],
    update_cards_use_case: NamedDependency[UpdateCardsUseCase],
) -> schemas.Cards:
    return schemas.Cards.from_models(await update_cards_use_case(deck_id=deck_id, data=data))


ROUTER: typing.Final = litestar.Router(
    path="/api",
    route_handlers=[list_cards, get_card, create_cards, update_cards],
)

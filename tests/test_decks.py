import pytest
from httpx import AsyncClient
from litestar import status_codes
from sqlalchemy.ext.asyncio import AsyncSession

from tests import factories


async def test_get_decks_empty(client: AsyncClient) -> None:
    response = await client.get("/api/decks/")
    assert response.status_code == status_codes.HTTP_200_OK, response.text
    assert len(response.json()["items"]) == 0


async def test_get_decks_not_exist(client: AsyncClient) -> None:
    response = await client.get("/api/decks/0/")
    assert response.status_code == status_codes.HTTP_404_NOT_FOUND, response.text


async def test_get_decks(client: AsyncClient, db_session: AsyncSession) -> None:
    factories.DeckModelFactory.__async_session__ = db_session
    deck = await factories.DeckModelFactory.create_async()

    response = await client.get("/api/decks/")
    assert response.status_code == status_codes.HTTP_200_OK, response.text
    data = response.json()
    assert len(data["items"]) == 1
    for k, v in data["items"][0].items():
        assert v == getattr(deck, k)


async def test_get_one_deck(client: AsyncClient, db_session: AsyncSession) -> None:
    factories.DeckModelFactory.__async_session__ = db_session
    factories.CardModelFactory.__async_session__ = db_session
    deck = await factories.DeckModelFactory.create_async()
    card = await factories.CardModelFactory.create_async(deck_id=deck.id)
    assert card.id

    response = await client.get(f"/api/decks/{deck.id}/")
    assert response.status_code == status_codes.HTTP_200_OK, response.text
    data = response.json()
    assert len(data["cards"]) == 1
    for k, v in data.items():
        if k == "cards":
            continue
        assert v == getattr(deck, k)


@pytest.mark.parametrize(
    ("name", "description", "status_code"),
    [
        (None, None, status_codes.HTTP_400_BAD_REQUEST),
        ("test deck", None, status_codes.HTTP_201_CREATED),
        ("test deck", "test deck description", status_codes.HTTP_201_CREATED),
    ],
)
async def test_post_decks(
    client: AsyncClient,
    name: str,
    description: str,
    status_code: int,
) -> None:
    # create deck
    response = await client.post(
        "/api/decks/",
        json={
            "name": name,
            "description": description,
        },
    )
    assert response.status_code == status_code, response.text

    # get item
    if status_code == status_codes.HTTP_201_CREATED:
        item_id = response.json()["id"]
        response = await client.get(f"/api/decks/{item_id}/")
        assert response.status_code == status_codes.HTTP_200_OK
        result = response.json()
        assert item_id == result["id"]
        assert name == result["name"]
        assert description == result["description"]


async def test_put_decks_wrong_body(client: AsyncClient, db_session: AsyncSession) -> None:
    factories.DeckModelFactory.__async_session__ = db_session
    deck = await factories.DeckModelFactory.create_async()

    # update deck
    response = await client.put(
        f"/api/decks/{deck.id}/",
        json={"name": None, "description": None},
    )
    assert response.status_code == status_codes.HTTP_400_BAD_REQUEST, response.text


async def test_put_decks_not_exist(client: AsyncClient) -> None:
    response = await client.put(
        "/api/decks/999/",
        json={"name": "some", "description": "some"},
    )
    assert response.status_code == status_codes.HTTP_404_NOT_FOUND, response.text


@pytest.mark.parametrize(
    ("name", "description"),
    [
        ("test deck updated", None),
        ("test deck updated", "test deck description updated"),
    ],
)
async def test_put_decks(
    client: AsyncClient,
    name: str,
    description: str,
    db_session: AsyncSession,
) -> None:
    factories.DeckModelFactory.__async_session__ = db_session
    deck = await factories.DeckModelFactory.create_async()

    # update deck
    response = await client.put(
        f"/api/decks/{deck.id}/",
        json={"name": name, "description": description},
    )
    assert response.status_code == status_codes.HTTP_200_OK, response.text

    # get item
    item_id = response.json()["id"]
    response = await client.get(f"/api/decks/{item_id}/")
    assert response.status_code == status_codes.HTTP_200_OK, response.text
    result = response.json()
    assert name == result["name"]
    assert description == result["description"]

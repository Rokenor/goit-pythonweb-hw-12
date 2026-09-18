"""Інтеграційні тести службових маршрутів."""

from unittest.mock import AsyncMock, MagicMock

from main import app
from src.database.db import get_db


def test_healthchecker(client):
    response = client.get("api/healthchecker")

    assert response.status_code == 200, response.text
    assert response.json() == {"message": "Welcome to FastAPI!"}


def test_healthchecker_without_database(client):
    original = app.dependency_overrides.get(get_db)

    async def broken_db():
        session = MagicMock()
        session.execute = AsyncMock(side_effect=RuntimeError("db is down"))
        yield session

    app.dependency_overrides[get_db] = broken_db
    try:
        response = client.get("api/healthchecker")
    finally:
        if original is not None:
            app.dependency_overrides[get_db] = original

    assert response.status_code == 500, response.text
    assert response.json()["detail"] == "Error connecting to the database"


def test_healthchecker_misconfigured_database(client):
    original = app.dependency_overrides.get(get_db)

    async def empty_db():
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        yield session

    app.dependency_overrides[get_db] = empty_db
    try:
        response = client.get("api/healthchecker")
    finally:
        if original is not None:
            app.dependency_overrides[get_db] = original

    assert response.status_code == 500, response.text
    assert response.json()["detail"] == "Database is not configured correctly"

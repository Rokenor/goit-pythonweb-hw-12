"""Модульні тести менеджера сесій бази даних."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.database.db import DatabaseSessionManager, get_db, sessionmanager
from tests.conftest import SQLALCHEMY_DATABASE_URL


@pytest.fixture
def manager():
    return DatabaseSessionManager(SQLALCHEMY_DATABASE_URL)


async def test_session_yields_working_session(manager):
    async with manager.session() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1


async def test_session_rolls_back_on_sqlalchemy_error(manager):
    with pytest.raises(SQLAlchemyError):
        async with manager.session() as session:
            await session.execute(text("SELECT * FROM table_that_does_not_exist"))


async def test_session_raises_without_session_maker(manager):
    manager._session_maker = None

    with pytest.raises(Exception, match="Database session is not initialized"):
        async with manager.session():
            pass


async def test_get_db_yields_session(monkeypatch, manager):
    monkeypatch.setattr(sessionmanager, "_session_maker", manager._session_maker)

    async for session in get_db():
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1

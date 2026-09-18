"""Керування підключенням до бази даних."""

import contextlib
from typing import AsyncIterator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.conf.config import config


class DatabaseSessionManager:
    """Створює асинхронні сесії SQLAlchemy й гарантує їх коректне закриття."""

    def __init__(self, url: str):
        """
        :param url: рядок підключення до бази даних.
        :type url: str
        """
        self._engine: AsyncEngine | None = create_async_engine(url)
        self._session_maker: async_sessionmaker = async_sessionmaker(
            autoflush=False, autocommit=False, bind=self._engine
        )

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Контекстний менеджер із сесією бази даних.

        У разі помилки SQLAlchemy транзакція відкочується, а сама помилка
        прокидається далі; сесія закривається в будь-якому випадку.

        :raises Exception: якщо фабрику сесій не ініціалізовано.
        :return: асинхронна сесія.
        :rtype: AsyncIterator[AsyncSession]
        """
        if self._session_maker is None:
            raise Exception("Database session is not initialized")
        session = self._session_maker()
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            raise  # прокидаємо початкову помилку далі
        finally:
            await session.close()


sessionmanager = DatabaseSessionManager(config.DB_URL)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Залежність FastAPI, що віддає сесію бази даних на час запиту.

    :return: асинхронна сесія.
    :rtype: AsyncIterator[AsyncSession]
    """
    async with sessionmanager.session() as session:
        yield session

"""Спільні фікстури для модульних та інтеграційних тестів.

Тести працюють на SQLite (``aiosqlite``) з єдиним з'єднанням у пулі, тому
жодна зовнішня служба для них не потрібна: Redis вимкнено, а лімітер
запитів відключено, щоб порядок тестів не впливав на результат.
"""

import asyncio

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from main import app
from src.conf.config import settings
from src.database.db import get_db
from src.database.models import Base, User, UserRole
from src.services.auth import Hash, create_access_token, create_refresh_token
from src.services.rate_limit import limiter

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
)

test_user = {
    "username": "deadpool",
    "email": "deadpool@example.com",
    "password": "12345678",
}

test_admin = {
    "username": "nickfury",
    "email": "nickfury@example.com",
    "password": "12345678",
}


@pytest.fixture(scope="session", autouse=True)
def disable_external_services():
    """Вимикає Redis і лімітер запитів на весь час прогону тестів."""
    redis_enabled = settings.REDIS_ENABLED
    limiter_enabled = limiter.enabled
    settings.REDIS_ENABLED = False
    limiter.enabled = False
    yield
    settings.REDIS_ENABLED = redis_enabled
    limiter.enabled = limiter_enabled


@pytest.fixture(scope="module", autouse=True)
def init_models_wrap():
    """Перестворює схему бази та наповнює її двома користувачами."""

    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        async with TestingSessionLocal() as session:
            hash_password = Hash().get_password_hash(test_user["password"])
            session.add(
                User(
                    username=test_user["username"],
                    email=test_user["email"],
                    hashed_password=hash_password,
                    confirmed=True,
                    avatar="https://twitter.com/gravatar",
                    role=UserRole.USER,
                )
            )
            session.add(
                User(
                    username=test_admin["username"],
                    email=test_admin["email"],
                    hashed_password=Hash().get_password_hash(test_admin["password"]),
                    confirmed=True,
                    avatar="https://twitter.com/gravatar",
                    role=UserRole.ADMIN,
                )
            )
            await session.commit()

    asyncio.run(init_models())


@pytest.fixture(scope="module")
def client():
    """Синхронний тестовий клієнт із підміненою залежністю бази даних."""

    async def override_get_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def get_token():
    """Access-токен звичайного користувача."""
    return await create_access_token(data={"sub": test_user["username"]})


@pytest_asyncio.fixture()
async def get_refresh_token():
    """Refresh-токен звичайного користувача."""
    return await create_refresh_token(data={"sub": test_user["username"]})


@pytest_asyncio.fixture()
async def get_admin_token():
    """Access-токен адміністратора."""
    return await create_access_token(data={"sub": test_admin["username"]})

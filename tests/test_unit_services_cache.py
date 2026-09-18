"""Модульні тести Redis-кешу користувача.

Справжній Redis не потрібен: замість нього використовується підроблений
клієнт, який ще й уміє імітувати відмову служби.
"""

from datetime import datetime

import pytest
from redis.exceptions import RedisError

from src.conf.config import settings
from src.database.models import User, UserRole
from src.services import cache as cache_module
from src.services.cache import (
    cache_user,
    close_redis,
    get_cached_user,
    get_redis,
    invalidate_user_cache,
)


class FakeRedis:
    """Мінімальний асинхронний замінник Redis для тестів."""

    def __init__(self, failing: bool = False):
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.failing = failing
        self.closed = False

    async def get(self, key):
        if self.failing:
            raise RedisError("down")
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        if self.failing:
            raise RedisError("down")
        self.store[key] = value
        self.ttls[key] = ex

    async def delete(self, key):
        if self.failing:
            raise RedisError("down")
        self.store.pop(key, None)

    async def aclose(self):
        self.closed = True


@pytest.fixture
def fake_redis(monkeypatch):
    client = FakeRedis()
    monkeypatch.setattr(cache_module, "get_redis", lambda: client)
    return client


@pytest.fixture
def user():
    return User(
        id=1,
        username="DeadPool",
        email="deadpool@example.com",
        hashed_password="super-secret-hash",
        avatar="https://avatar",
        confirmed=True,
        role=UserRole.ADMIN,
        created_at=datetime(2026, 1, 1, 12, 0, 0),
    )


async def test_cache_roundtrip(fake_redis, user):
    await cache_user(user)
    cached = await get_cached_user("deadpool")

    assert cached is not None
    assert cached.id == user.id
    assert cached.username == user.username
    assert cached.email == user.email
    assert cached.confirmed is True
    assert cached.role == UserRole.ADMIN
    assert cached.created_at == user.created_at


async def test_cache_does_not_store_password_hash(fake_redis, user):
    await cache_user(user)

    raw = fake_redis.store["user:deadpool"]
    assert "super-secret-hash" not in raw
    assert "hashed_password" not in raw


async def test_cache_entry_has_ttl(fake_redis, user):
    await cache_user(user)

    assert fake_redis.ttls["user:deadpool"] == settings.USER_CACHE_TTL


async def test_get_cached_user_miss(fake_redis):
    assert await get_cached_user("nobody") is None


async def test_invalidate_user_cache(fake_redis, user):
    await cache_user(user)
    await invalidate_user_cache(user.username)

    assert await get_cached_user(user.username) is None


async def test_invalidate_user_cache_ignores_none(fake_redis, user):
    await cache_user(user)
    await invalidate_user_cache(None)

    assert fake_redis.store  # запис лишився на місці


async def test_corrupted_entry_is_dropped(fake_redis, user):
    fake_redis.store["user:deadpool"] = "{not json"

    assert await get_cached_user("deadpool") is None
    assert "user:deadpool" not in fake_redis.store


async def test_cache_survives_redis_failure(monkeypatch, user):
    failing = FakeRedis(failing=True)
    monkeypatch.setattr(cache_module, "get_redis", lambda: failing)

    await cache_user(user)  # не має кидати виняток
    assert await get_cached_user(user.username) is None
    await invalidate_user_cache(user.username)


async def test_no_client_when_cache_disabled(monkeypatch, user):
    monkeypatch.setattr(settings, "REDIS_ENABLED", False)
    monkeypatch.setattr(cache_module, "_redis_client", None)

    assert get_redis() is None
    assert await get_cached_user("deadpool") is None
    await cache_user(user)
    await invalidate_user_cache("deadpool")


async def test_get_redis_reuses_client(monkeypatch):
    monkeypatch.setattr(settings, "REDIS_ENABLED", True)
    monkeypatch.setattr(cache_module, "_redis_client", None)

    first = get_redis()
    second = get_redis()

    assert first is second
    monkeypatch.setattr(cache_module, "_redis_client", None)


async def test_close_redis(monkeypatch):
    client = FakeRedis()
    monkeypatch.setattr(cache_module, "_redis_client", client)

    await close_redis()

    assert client.closed is True
    assert cache_module._redis_client is None


async def test_close_redis_without_client(monkeypatch):
    monkeypatch.setattr(cache_module, "_redis_client", None)

    await close_redis()  # не має нічого робити й не має падати


async def test_close_redis_survives_failure(monkeypatch):
    class FailingOnClose(FakeRedis):
        async def aclose(self):
            raise RedisError("cannot close")

    monkeypatch.setattr(cache_module, "_redis_client", FailingOnClose())

    await close_redis()

    assert cache_module._redis_client is None

"""Модульні тести сервісу користувачів: Gravatar і скидання кешу."""

from unittest.mock import AsyncMock, patch

import pytest

from src.database.models import User, UserRole
from src.schemas import UserCreate
from src.services.users import UserService


@pytest.fixture
def service():
    service = UserService(AsyncMock())
    service.repository = AsyncMock()
    return service


@pytest.fixture
def stored_user():
    return User(
        id=1,
        username="deadpool",
        email="deadpool@example.com",
        hashed_password="hash",
        role=UserRole.USER,
    )


@pytest.fixture
def body():
    return UserCreate(
        username="deadpool", email="deadpool@example.com", password="12345678"
    )


async def test_create_user_uses_gravatar(service, body, stored_user):
    service.repository.create_user.return_value = stored_user
    with patch("src.services.users.Gravatar") as gravatar:
        gravatar.return_value.get_image.return_value = "https://gravatar/img"
        user = await service.create_user(body, "hash")

    assert user is stored_user
    service.repository.create_user.assert_awaited_once_with(
        body, "hash", "https://gravatar/img"
    )


async def test_create_user_survives_gravatar_failure(service, body, stored_user):
    service.repository.create_user.return_value = stored_user
    with patch("src.services.users.Gravatar", side_effect=RuntimeError("no network")):
        user = await service.create_user(body, "hash")

    assert user is stored_user
    service.repository.create_user.assert_awaited_once_with(body, "hash", None)


async def test_getters_delegate_to_repository(service, stored_user):
    service.repository.get_user_by_id.return_value = stored_user
    service.repository.get_user_by_username.return_value = stored_user
    service.repository.get_user_by_email.return_value = stored_user

    assert await service.get_user_by_id(1) is stored_user
    assert await service.get_user_by_username("deadpool") is stored_user
    assert await service.get_user_by_email("deadpool@example.com") is stored_user


async def test_confirmed_email_invalidates_cache(service, stored_user):
    service.repository.confirmed_email.return_value = stored_user
    with patch(
        "src.services.users.invalidate_user_cache", new=AsyncMock()
    ) as invalidate:
        await service.confirmed_email(stored_user.email)

    invalidate.assert_awaited_once_with(stored_user.username)


async def test_update_avatar_invalidates_cache(service, stored_user):
    service.repository.update_avatar_url.return_value = stored_user
    with patch(
        "src.services.users.invalidate_user_cache", new=AsyncMock()
    ) as invalidate:
        user = await service.update_avatar_url(stored_user.email, "https://new")

    assert user is stored_user
    invalidate.assert_awaited_once_with(stored_user.username)


async def test_update_password_invalidates_cache(service, stored_user):
    service.repository.update_password.return_value = stored_user
    with patch(
        "src.services.users.invalidate_user_cache", new=AsyncMock()
    ) as invalidate:
        await service.update_password(stored_user.email, "new-hash")

    invalidate.assert_awaited_once_with(stored_user.username)


async def test_update_password_unknown_user_skips_invalidation(service):
    service.repository.update_password.return_value = None
    with patch(
        "src.services.users.invalidate_user_cache", new=AsyncMock()
    ) as invalidate:
        assert await service.update_password("ghost@example.com", "hash") is None

    invalidate.assert_awaited_once_with(None)

"""Модульні тести сервісу аутентифікації: паролі, токени, ролі, кеш."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from jose import jwt

from src.conf.config import settings
from src.database.models import User, UserRole
from src.services.auth import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    Hash,
    create_access_token,
    create_email_token,
    create_password_reset_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_admin_user,
    get_current_user,
    get_email_from_reset_token,
    get_email_from_token,
)


def _payload(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


@pytest.fixture
def user():
    return User(
        id=1,
        username="deadpool",
        email="deadpool@example.com",
        hashed_password="hash",
        role=UserRole.USER,
    )


@pytest.fixture
def admin():
    return User(
        id=2,
        username="nickfury",
        email="nickfury@example.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
    )


# ------------------------------------------------------------------ паролі --
def test_password_hash_roundtrip():
    hasher = Hash()
    hashed = hasher.get_password_hash("12345678")

    assert hashed != "12345678"
    assert hasher.verify_password("12345678", hashed) is True
    assert hasher.verify_password("wrong-password", hashed) is False


# ------------------------------------------------------------------ токени --
async def test_access_and_refresh_tokens_differ():
    access = await create_access_token({"sub": "deadpool"})
    refresh = await create_refresh_token({"sub": "deadpool"})

    assert access != refresh
    assert _payload(access)["token_type"] == TOKEN_TYPE_ACCESS
    assert _payload(refresh)["token_type"] == TOKEN_TYPE_REFRESH
    assert _payload(refresh)["exp"] > _payload(access)["exp"]


async def test_custom_expiration_is_respected():
    token = await create_access_token({"sub": "deadpool"}, expires_delta=60)
    payload = _payload(token)

    assert payload["exp"] - payload["iat"] == 60


async def test_decode_refresh_token_returns_username():
    token = await create_refresh_token({"sub": "deadpool"})

    assert await decode_refresh_token(token) == "deadpool"


async def test_access_token_rejected_as_refresh():
    token = await create_access_token({"sub": "deadpool"})

    with pytest.raises(HTTPException) as exc:
        await decode_refresh_token(token)
    assert exc.value.status_code == 401


async def test_decode_refresh_token_rejects_garbage():
    with pytest.raises(HTTPException) as exc:
        await decode_refresh_token("not-a-token")
    assert exc.value.status_code == 401


async def test_decode_refresh_token_without_subject():
    token = await create_refresh_token({})

    with pytest.raises(HTTPException) as exc:
        await decode_refresh_token(token)
    assert exc.value.status_code == 401


async def test_email_token_roundtrip():
    token = create_email_token({"sub": "deadpool@example.com"})

    assert await get_email_from_token(token) == "deadpool@example.com"


async def test_email_token_rejects_other_types():
    token = create_password_reset_token("deadpool@example.com")

    with pytest.raises(HTTPException) as exc:
        await get_email_from_token(token)
    assert exc.value.status_code == 422


async def test_reset_token_roundtrip():
    token = create_password_reset_token("deadpool@example.com")

    assert await get_email_from_reset_token(token) == "deadpool@example.com"


async def test_reset_token_rejects_email_token():
    token = create_email_token({"sub": "deadpool@example.com"})

    with pytest.raises(HTTPException) as exc:
        await get_email_from_reset_token(token)
    assert exc.value.status_code == 422


async def test_reset_token_rejects_expired_token():
    token = create_password_reset_token("deadpool@example.com")
    with patch.object(settings, "PASSWORD_RESET_EXPIRATION_SECONDS", -1):
        expired = create_password_reset_token("deadpool@example.com")

    assert await get_email_from_reset_token(token) == "deadpool@example.com"
    with pytest.raises(HTTPException) as exc:
        await get_email_from_reset_token(expired)
    assert exc.value.status_code == 422


# ---------------------------------------------------- поточний користувач --
async def test_get_current_user_from_cache(user):
    token = await create_access_token({"sub": user.username})
    user_service = AsyncMock()

    with (
        patch("src.services.auth.get_cached_user", new=AsyncMock(return_value=user)),
        patch("src.services.auth.UserService", return_value=user_service),
    ):
        result = await get_current_user(token=token, db=AsyncMock())

    assert result is user
    user_service.get_user_by_username.assert_not_called()


async def test_get_current_user_falls_back_to_db_and_caches(user):
    token = await create_access_token({"sub": user.username})
    user_service = AsyncMock()
    user_service.get_user_by_username.return_value = user

    with (
        patch("src.services.auth.get_cached_user", new=AsyncMock(return_value=None)),
        patch("src.services.auth.cache_user", new=AsyncMock()) as cache_user_mock,
        patch("src.services.auth.UserService", return_value=user_service),
    ):
        result = await get_current_user(token=token, db=AsyncMock())

    assert result is user
    user_service.get_user_by_username.assert_awaited_once_with(user.username)
    cache_user_mock.assert_awaited_once_with(user)


async def test_get_current_user_rejects_refresh_token(user):
    token = await create_refresh_token({"sub": user.username})

    with pytest.raises(HTTPException) as exc:
        await get_current_user(token=token, db=AsyncMock())
    assert exc.value.status_code == 401


async def test_get_current_user_rejects_invalid_token():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token="broken", db=AsyncMock())
    assert exc.value.status_code == 401


async def test_get_current_user_without_subject():
    token = await create_access_token({})

    with patch("src.services.auth.get_cached_user", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(token=token, db=AsyncMock())
    assert exc.value.status_code == 401


async def test_get_current_user_unknown_user():
    token = await create_access_token({"sub": "ghost"})
    user_service = AsyncMock()
    user_service.get_user_by_username.return_value = None

    with (
        patch("src.services.auth.get_cached_user", new=AsyncMock(return_value=None)),
        patch("src.services.auth.UserService", return_value=user_service),
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(token=token, db=AsyncMock())
    assert exc.value.status_code == 401


# --------------------------------------------------------------------ролі --
async def test_admin_dependency_allows_admin(admin):
    assert await get_current_admin_user(user=admin) is admin


async def test_admin_dependency_blocks_regular_user(user):
    with pytest.raises(HTTPException) as exc:
        await get_current_admin_user(user=user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Недостатньо прав доступу"

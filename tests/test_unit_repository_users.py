"""Модульні тести репозиторію користувачів на мокнутій сесії SQLAlchemy."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User, UserRole
from src.repository.users import UserRepository
from src.schemas import UserCreate


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def user_repository(mock_session):
    return UserRepository(mock_session)


@pytest.fixture
def existing_user():
    return User(
        id=1,
        username="deadpool",
        email="deadpool@example.com",
        hashed_password="old-hash",
        confirmed=False,
        role=UserRole.USER,
    )


def _scalar_one_or_none(item):
    result = MagicMock()
    result.scalar_one_or_none.return_value = item
    return result


async def test_get_user_by_id(user_repository, mock_session, existing_user):
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(existing_user))

    user = await user_repository.get_user_by_id(1)

    assert user is existing_user


async def test_get_user_by_id_not_found(user_repository, mock_session):
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))

    assert await user_repository.get_user_by_id(42) is None


async def test_get_user_by_username(user_repository, mock_session, existing_user):
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(existing_user))

    user = await user_repository.get_user_by_username("DeadPool")

    assert user is existing_user
    assert "lower(users.username)" in str(mock_session.execute.await_args.args[0])


async def test_get_user_by_email(user_repository, mock_session, existing_user):
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(existing_user))

    user = await user_repository.get_user_by_email("DEADPOOL@example.com")

    assert user is existing_user
    assert "lower(users.email)" in str(mock_session.execute.await_args.args[0])


async def test_create_user_default_role(user_repository, mock_session):
    body = UserCreate(
        username="newbie", email="newbie@example.com", password="12345678"
    )

    user = await user_repository.create_user(body, "hashed", "https://avatar")

    assert user.username == "newbie"
    assert user.hashed_password == "hashed"
    assert user.avatar == "https://avatar"
    assert user.role == UserRole.USER
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(user)


async def test_create_user_admin_role(user_repository, mock_session):
    body = UserCreate(
        username="boss",
        email="boss@example.com",
        password="12345678",
        role=UserRole.ADMIN,
    )

    user = await user_repository.create_user(body, "hashed")

    assert user.role == UserRole.ADMIN
    assert user.avatar is None


async def test_confirmed_email(user_repository, mock_session, existing_user):
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(existing_user))

    user = await user_repository.confirmed_email(existing_user.email)

    assert user.confirmed is True
    mock_session.commit.assert_awaited_once()


async def test_confirmed_email_unknown_user(user_repository, mock_session):
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))

    assert await user_repository.confirmed_email("ghost@example.com") is None
    mock_session.commit.assert_not_awaited()


async def test_update_avatar_url(user_repository, mock_session, existing_user):
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(existing_user))

    user = await user_repository.update_avatar_url(
        existing_user.email, "https://new-avatar"
    )

    assert user.avatar == "https://new-avatar"
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(existing_user)


async def test_update_avatar_url_unknown_user(user_repository, mock_session):
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))

    assert await user_repository.update_avatar_url("ghost@example.com", "url") is None


async def test_update_password(user_repository, mock_session, existing_user):
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(existing_user))

    user = await user_repository.update_password(existing_user.email, "new-hash")

    assert user.hashed_password == "new-hash"
    mock_session.commit.assert_awaited_once()


async def test_update_password_unknown_user(user_repository, mock_session):
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))

    assert await user_repository.update_password("ghost@example.com", "hash") is None
    mock_session.commit.assert_not_awaited()

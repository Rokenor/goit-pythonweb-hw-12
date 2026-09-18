"""Модульні тести репозиторію контактів на мокнутій сесії SQLAlchemy."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.repository.contacts import ContactRepository
from src.schemas import ContactModel


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def contact_repository(mock_session):
    return ContactRepository(mock_session)


@pytest.fixture
def user():
    return User(id=1, username="testuser", email="testuser@example.com")


@pytest.fixture
def contact_body():
    return ContactModel(
        first_name="Іван",
        last_name="Петренко",
        email="ivan.petrenko@example.com",
        phone="+380501234567",
        birthday=date(1990, 4, 15),
        additional_data="Друг з університету",
    )


def _scalars_all(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _scalar_one_or_none(item):
    result = MagicMock()
    result.scalar_one_or_none.return_value = item
    return result


async def test_get_contacts(contact_repository, mock_session, user):
    expected = [
        Contact(id=1, first_name="Іван", last_name="Петренко", user_id=user.id)
    ]
    mock_session.execute = AsyncMock(return_value=_scalars_all(expected))

    contacts = await contact_repository.get_contacts(user, skip=0, limit=10)

    assert len(contacts) == 1
    assert contacts[0].first_name == "Іван"
    mock_session.execute.assert_awaited_once()


async def test_get_contacts_with_filters(contact_repository, mock_session, user):
    mock_session.execute = AsyncMock(return_value=_scalars_all([]))

    contacts = await contact_repository.get_contacts(
        user,
        skip=5,
        limit=10,
        first_name="Іван",
        last_name="Петренко",
        email="example.com",
    )

    assert contacts == []
    stmt = str(mock_session.execute.await_args.args[0])
    assert "lower(contacts.first_name) LIKE lower" in stmt
    assert "lower(contacts.last_name) LIKE lower" in stmt
    assert "lower(contacts.email) LIKE lower" in stmt


async def test_get_contact_by_id_found(contact_repository, mock_session, user):
    expected = Contact(id=7, first_name="Іван", user_id=user.id)
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(expected))

    contact = await contact_repository.get_contact_by_id(7, user)

    assert contact is not None
    assert contact.id == 7


async def test_get_contact_by_id_not_found(contact_repository, mock_session, user):
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))

    assert await contact_repository.get_contact_by_id(404, user) is None


async def test_get_contact_by_email(contact_repository, mock_session, user):
    expected = Contact(id=1, email="ivan@example.com", user_id=user.id)
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(expected))

    contact = await contact_repository.get_contact_by_email("IVAN@EXAMPLE.COM", user)

    assert contact is expected


async def test_create_contact(contact_repository, mock_session, user, contact_body):
    result = await contact_repository.create_contact(contact_body, user)

    assert isinstance(result, Contact)
    assert result.first_name == contact_body.first_name
    assert result.user_id == user.id
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(result)


async def test_update_contact(contact_repository, mock_session, user, contact_body):
    existing = Contact(id=1, first_name="Старе", last_name="Імʼя", user_id=user.id)
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(existing))

    result = await contact_repository.update_contact(1, contact_body, user)

    assert result is existing
    assert result.first_name == contact_body.first_name
    assert result.phone == contact_body.phone
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(existing)


async def test_update_contact_not_found(
    contact_repository, mock_session, user, contact_body
):
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))

    assert await contact_repository.update_contact(1, contact_body, user) is None
    mock_session.commit.assert_not_awaited()


async def test_remove_contact(contact_repository, mock_session, user):
    existing = Contact(id=1, first_name="Іван", user_id=user.id)
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(existing))

    result = await contact_repository.remove_contact(1, user)

    assert result is existing
    mock_session.delete.assert_awaited_once_with(existing)
    mock_session.commit.assert_awaited_once()


async def test_remove_contact_not_found(contact_repository, mock_session, user):
    mock_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))

    assert await contact_repository.remove_contact(1, user) is None
    mock_session.delete.assert_not_awaited()


async def test_get_upcoming_birthdays(contact_repository, mock_session, user):
    expected = [Contact(id=1, birthday=date(1990, 4, 15), user_id=user.id)]
    mock_session.execute = AsyncMock(return_value=_scalars_all(expected))

    contacts = await contact_repository.get_upcoming_birthdays(user, days=7)

    assert contacts == expected
    stmt = str(mock_session.execute.await_args.args[0])
    assert "EXTRACT(month FROM contacts.birthday)" in stmt
    assert "EXTRACT(day FROM contacts.birthday)" in stmt

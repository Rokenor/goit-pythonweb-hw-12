"""Модульні тести сервісу контактів — перевіряють делегування репозиторію."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.database.models import Contact, User
from src.schemas import ContactModel
from src.services.contacts import ContactService


@pytest.fixture
def service():
    service = ContactService(AsyncMock())
    service.repository = AsyncMock()
    return service


@pytest.fixture
def user():
    return User(id=1, username="deadpool")


@pytest.fixture
def body():
    return ContactModel(
        first_name="Іван",
        last_name="Петренко",
        email="ivan@example.com",
        phone="+380501234567",
        birthday=date(1990, 4, 15),
    )


async def test_create_contact(service, body, user):
    contact = Contact(id=1)
    service.repository.create_contact.return_value = contact

    assert await service.create_contact(body, user) is contact
    service.repository.create_contact.assert_awaited_once_with(body, user)


async def test_get_contacts(service, user):
    service.repository.get_contacts.return_value = []

    assert await service.get_contacts(user, 0, 10, "Іван", None, None) == []
    service.repository.get_contacts.assert_awaited_once_with(
        user, 0, 10, "Іван", None, None
    )


async def test_get_contact(service, user):
    contact = Contact(id=5)
    service.repository.get_contact_by_id.return_value = contact

    assert await service.get_contact(5, user) is contact
    service.repository.get_contact_by_id.assert_awaited_once_with(5, user)


async def test_get_contact_by_email(service, user):
    service.repository.get_contact_by_email.return_value = None

    assert await service.get_contact_by_email("ivan@example.com", user) is None


async def test_update_contact(service, body, user):
    contact = Contact(id=5)
    service.repository.update_contact.return_value = contact

    assert await service.update_contact(5, body, user) is contact
    service.repository.update_contact.assert_awaited_once_with(5, body, user)


async def test_remove_contact(service, user):
    contact = Contact(id=5)
    service.repository.remove_contact.return_value = contact

    assert await service.remove_contact(5, user) is contact
    service.repository.remove_contact.assert_awaited_once_with(5, user)


async def test_get_upcoming_birthdays(service, user):
    service.repository.get_upcoming_birthdays.return_value = []

    assert await service.get_upcoming_birthdays(user, 14) == []
    service.repository.get_upcoming_birthdays.assert_awaited_once_with(user, 14)

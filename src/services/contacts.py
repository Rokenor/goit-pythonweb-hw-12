"""Бізнес-логіка роботи з контактами.

Сервіс є тонким прошарком над :class:`~src.repository.contacts.ContactRepository`
і відокремлює маршрути від безпосередніх запитів до бази.
"""

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.repository.contacts import ContactRepository
from src.schemas import ContactModel


class ContactService:
    """Операції над контактами поточного користувача."""

    def __init__(self, db: AsyncSession):
        """
        :param db: асинхронна сесія SQLAlchemy.
        :type db: AsyncSession
        """
        self.repository = ContactRepository(db)

    async def create_contact(self, body: ContactModel, user: User) -> Contact:
        """Створює контакт для користувача.

        :param body: дані нового контакту.
        :type body: ContactModel
        :param user: власник контакту.
        :type user: User
        :return: збережений контакт.
        :rtype: Contact
        """
        return await self.repository.create_contact(body, user)

    async def get_contacts(
        self,
        user: User,
        skip: int,
        limit: int,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
    ) -> Sequence[Contact]:
        """Повертає контакти користувача з пагінацією та пошуком.

        :param user: власник контактів.
        :type user: User
        :param skip: скільки записів пропустити.
        :type skip: int
        :param limit: максимальна кількість записів у відповіді.
        :type limit: int
        :param first_name: фільтр за іменем (частковий збіг).
        :type first_name: str | None
        :param last_name: фільтр за прізвищем (частковий збіг).
        :type last_name: str | None
        :param email: фільтр за електронною адресою (частковий збіг).
        :type email: str | None
        :return: знайдені контакти.
        :rtype: Sequence[Contact]
        """
        return await self.repository.get_contacts(
            user, skip, limit, first_name, last_name, email
        )

    async def get_contact(self, contact_id: int, user: User) -> Contact | None:
        """Повертає контакт користувача за ідентифікатором.

        :param contact_id: ідентифікатор контакту.
        :type contact_id: int
        :param user: власник контакту.
        :type user: User
        :return: контакт або ``None``.
        :rtype: Contact | None
        """
        return await self.repository.get_contact_by_id(contact_id, user)

    async def get_contact_by_email(self, email: str, user: User) -> Contact | None:
        """Повертає контакт користувача за електронною адресою.

        :param email: електронна адреса контакту.
        :type email: str
        :param user: власник контакту.
        :type user: User
        :return: контакт або ``None``.
        :rtype: Contact | None
        """
        return await self.repository.get_contact_by_email(email, user)

    async def update_contact(
        self, contact_id: int, body: ContactModel, user: User
    ) -> Contact | None:
        """Оновлює контакт користувача.

        :param contact_id: ідентифікатор контакту.
        :type contact_id: int
        :param body: нові значення полів.
        :type body: ContactModel
        :param user: власник контакту.
        :type user: User
        :return: оновлений контакт або ``None``.
        :rtype: Contact | None
        """
        return await self.repository.update_contact(contact_id, body, user)

    async def remove_contact(self, contact_id: int, user: User) -> Contact | None:
        """Видаляє контакт користувача.

        :param contact_id: ідентифікатор контакту.
        :type contact_id: int
        :param user: власник контакту.
        :type user: User
        :return: видалений контакт або ``None``.
        :rtype: Contact | None
        """
        return await self.repository.remove_contact(contact_id, user)

    async def get_upcoming_birthdays(
        self, user: User, days: int = 7
    ) -> Sequence[Contact]:
        """Контакти з днями народження в найближчі ``days`` днів.

        :param user: власник контактів.
        :type user: User
        :param days: розмір вікна в днях.
        :type days: int
        :return: контакти з найближчими днями народження.
        :rtype: Sequence[Contact]
        """
        return await self.repository.get_upcoming_birthdays(user, days)

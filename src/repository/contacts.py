"""Доступ до таблиці контактів.

Кожен метод обмежений контактами власника, тому користувач принципово
не може дістатися чужих записів.
"""

from datetime import date, timedelta
from typing import Sequence

from sqlalchemy import Select, and_, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.schemas import ContactModel


class ContactRepository:
    """CRUD-операції над контактами в межах одного власника."""

    def __init__(self, session: AsyncSession):
        """
        :param session: асинхронна сесія SQLAlchemy.
        :type session: AsyncSession
        """
        self.db = session

    async def get_contacts(
        self,
        user: User,
        skip: int = 0,
        limit: int = 100,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
    ) -> Sequence[Contact]:
        """Повертає контакти користувача з пагінацією та пошуком.

        Непорожні пошукові параметри комбінуються через ``AND`` і
        застосовуються як частковий збіг без урахування регістру.

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
        :return: знайдені контакти, упорядковані за ``id``.
        :rtype: Sequence[Contact]
        """
        stmt: Select = select(Contact).where(Contact.user_id == user.id)
        if first_name:
            stmt = stmt.where(Contact.first_name.ilike(f"%{first_name}%"))
        if last_name:
            stmt = stmt.where(Contact.last_name.ilike(f"%{last_name}%"))
        if email:
            stmt = stmt.where(Contact.email.ilike(f"%{email}%"))
        stmt = stmt.order_by(Contact.id).offset(skip).limit(limit)
        contacts = await self.db.execute(stmt)
        return contacts.scalars().all()

    async def get_contact_by_id(self, contact_id: int, user: User) -> Contact | None:
        """Повертає контакт користувача за ідентифікатором.

        :param contact_id: ідентифікатор контакту.
        :type contact_id: int
        :param user: власник контакту.
        :type user: User
        :return: контакт або ``None``, якщо його немає в цього користувача.
        :rtype: Contact | None
        """
        stmt = select(Contact).filter_by(id=contact_id, user_id=user.id)
        contact = await self.db.execute(stmt)
        return contact.scalar_one_or_none()

    async def get_contact_by_email(self, email: str, user: User) -> Contact | None:
        """Повертає контакт користувача за електронною адресою.

        :param email: електронна адреса контакту.
        :type email: str
        :param user: власник контакту.
        :type user: User
        :return: контакт або ``None``.
        :rtype: Contact | None
        """
        stmt = select(Contact).where(
            func.lower(Contact.email) == email.lower(), Contact.user_id == user.id
        )
        contact = await self.db.execute(stmt)
        return contact.scalar_one_or_none()

    async def create_contact(self, body: ContactModel, user: User) -> Contact:
        """Створює контакт і прив'язує його до користувача.

        :param body: дані нового контакту.
        :type body: ContactModel
        :param user: власник контакту.
        :type user: User
        :return: збережений контакт.
        :rtype: Contact
        """
        contact = Contact(**body.model_dump(exclude_unset=True), user_id=user.id)
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def update_contact(
        self, contact_id: int, body: ContactModel, user: User
    ) -> Contact | None:
        """Оновлює поля контакту користувача.

        :param contact_id: ідентифікатор контакту.
        :type contact_id: int
        :param body: нові значення полів.
        :type body: ContactModel
        :param user: власник контакту.
        :type user: User
        :return: оновлений контакт або ``None``, якщо його не знайдено.
        :rtype: Contact | None
        """
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            for key, value in body.model_dump(exclude_unset=True).items():
                setattr(contact, key, value)
            await self.db.commit()
            await self.db.refresh(contact)
        return contact

    async def remove_contact(self, contact_id: int, user: User) -> Contact | None:
        """Видаляє контакт користувача.

        :param contact_id: ідентифікатор контакту.
        :type contact_id: int
        :param user: власник контакту.
        :type user: User
        :return: видалений контакт або ``None``, якщо його не знайдено.
        :rtype: Contact | None
        """
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            await self.db.delete(contact)
            await self.db.commit()
        return contact

    async def get_upcoming_birthdays(
        self, user: User, days: int = 7
    ) -> Sequence[Contact]:
        """Контакти, у яких день народження впродовж найближчих ``days`` днів.

        Порівнюються лише місяць і день, тому вікно коректно працює на межі
        року (напр. 28.12 -> 03.01) незалежно від року народження.

        :param user: власник контактів.
        :type user: User
        :param days: розмір вікна в днях, рахуючи від сьогодні.
        :type days: int
        :return: контакти з найближчими днями народження.
        :rtype: Sequence[Contact]
        """
        today = date.today()
        window = {
            (day.month, day.day)
            for day in (today + timedelta(days=offset) for offset in range(days))
        }
        # `extract` замість форматування дати рядком: так умова лишається
        # придатною для будь-якого діалекту, з яким працює SQLAlchemy.
        day_matches = [
            and_(
                extract("month", Contact.birthday) == month,
                extract("day", Contact.birthday) == day,
            )
            for month, day in sorted(window)
        ]
        stmt = (
            select(Contact)
            .where(Contact.user_id == user.id, or_(*day_matches))
            .order_by(Contact.id)
        )
        contacts = await self.db.execute(stmt)
        return contacts.scalars().all()

from datetime import date, timedelta
from typing import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.schemas import ContactModel


class ContactRepository:
    """Доступ до контактів. Кожен запит обмежений контактами власника."""

    def __init__(self, session: AsyncSession):
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
        stmt = select(Contact).filter_by(id=contact_id, user_id=user.id)
        contact = await self.db.execute(stmt)
        return contact.scalar_one_or_none()

    async def get_contact_by_email(self, email: str, user: User) -> Contact | None:
        stmt = select(Contact).where(
            func.lower(Contact.email) == email.lower(), Contact.user_id == user.id
        )
        contact = await self.db.execute(stmt)
        return contact.scalar_one_or_none()

    async def create_contact(self, body: ContactModel, user: User) -> Contact:
        contact = Contact(**body.model_dump(exclude_unset=True), user_id=user.id)
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def update_contact(
        self, contact_id: int, body: ContactModel, user: User
    ) -> Contact | None:
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            for key, value in body.model_dump(exclude_unset=True).items():
                setattr(contact, key, value)
            await self.db.commit()
            await self.db.refresh(contact)
        return contact

    async def remove_contact(self, contact_id: int, user: User) -> Contact | None:
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            await self.db.delete(contact)
            await self.db.commit()
        return contact

    async def get_upcoming_birthdays(
        self, user: User, days: int = 7
    ) -> Sequence[Contact]:
        """Контакти, у яких день народження впродовж найближчих `days` днів.

        Порівнюються лише місяць і день, тому вікно коректно працює на межі
        року (напр. 28.12 -> 03.01) незалежно від року народження.
        """
        today = date.today()
        month_days = {
            (today + timedelta(days=offset)).strftime("%m-%d") for offset in range(days)
        }
        stmt = (
            select(Contact)
            .where(
                Contact.user_id == user.id,
                func.to_char(Contact.birthday, "MM-DD").in_(month_days),
            )
            .order_by(Contact.id)
        )
        contacts = await self.db.execute(stmt)
        return contacts.scalars().all()

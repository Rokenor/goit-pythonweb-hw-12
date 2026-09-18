from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.repository.contacts import ContactRepository
from src.schemas import ContactModel


class ContactService:
    def __init__(self, db: AsyncSession):
        self.repository = ContactRepository(db)

    async def create_contact(self, body: ContactModel, user: User):
        return await self.repository.create_contact(body, user)

    async def get_contacts(
        self,
        user: User,
        skip: int,
        limit: int,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
    ):
        return await self.repository.get_contacts(
            user, skip, limit, first_name, last_name, email
        )

    async def get_contact(self, contact_id: int, user: User):
        return await self.repository.get_contact_by_id(contact_id, user)

    async def get_contact_by_email(self, email: str, user: User):
        return await self.repository.get_contact_by_email(email, user)

    async def update_contact(self, contact_id: int, body: ContactModel, user: User):
        return await self.repository.update_contact(contact_id, body, user)

    async def remove_contact(self, contact_id: int, user: User):
        return await self.repository.remove_contact(contact_id, user)

    async def get_upcoming_birthdays(self, user: User, days: int = 7):
        return await self.repository.get_upcoming_birthdays(user, days)

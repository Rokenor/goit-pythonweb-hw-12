from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.database.models import User
from src.schemas import ContactModel, ContactResponse
from src.services.auth import get_current_user
from src.services.contacts import ContactService

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/", response_model=List[ContactResponse])
async def read_contacts(
    skip: int = Query(0, ge=0, description="Скільки записів пропустити"),
    limit: int = Query(100, ge=1, le=1000, description="Максимум записів у відповіді"),
    first_name: str | None = Query(None, description="Пошук за іменем (частковий збіг)"),
    last_name: str | None = Query(None, description="Пошук за прізвищем (частковий збіг)"),
    email: str | None = Query(None, description="Пошук за email (частковий збіг)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Список власних контактів з пагінацією та пошуком за іменем, прізвищем чи email."""
    contact_service = ContactService(db)
    return await contact_service.get_contacts(
        user, skip, limit, first_name, last_name, email
    )


@router.get("/birthdays", response_model=List[ContactResponse])
async def read_upcoming_birthdays(
    days: int = Query(7, ge=1, le=365, description="Розмір вікна в днях (з сьогодні)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Контакти, у яких день народження протягом найближчих `days` днів."""
    contact_service = ContactService(db)
    return await contact_service.get_upcoming_birthdays(user, days)


@router.get("/{contact_id}", response_model=ContactResponse)
async def read_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contact_service = ContactService(db)
    contact = await contact_service.get_contact(contact_id, user)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return contact


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    body: ContactModel,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contact_service = ContactService(db)
    if await contact_service.get_contact_by_email(body.email, user):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contact with this email already exists",
        )
    return await contact_service.create_contact(body, user)


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    body: ContactModel,
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contact_service = ContactService(db)
    if await contact_service.get_contact(contact_id, user) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    duplicate = await contact_service.get_contact_by_email(body.email, user)
    if duplicate and duplicate.id != contact_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contact with this email already exists",
        )
    return await contact_service.update_contact(contact_id, body, user)


@router.delete("/{contact_id}", response_model=ContactResponse)
async def remove_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contact_service = ContactService(db)
    contact = await contact_service.remove_contact(contact_id, user)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return contact

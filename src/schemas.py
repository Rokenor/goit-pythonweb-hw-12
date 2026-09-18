"""Pydantic-схеми запитів і відповідей REST API."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.database.models import UserRole


# ---------------------------------------------------------------- контакти --
class ContactBase(BaseModel):
    """Спільні поля контакту для запитів і відповідей."""

    first_name: str = Field(min_length=1, max_length=50, examples=["Іван"])
    last_name: str = Field(min_length=1, max_length=50, examples=["Петренко"])
    email: EmailStr = Field(max_length=100, examples=["ivan.petrenko@example.com"])
    phone: str = Field(min_length=5, max_length=25, examples=["+380501234567"])
    birthday: date = Field(examples=["1990-04-15"])
    additional_data: str | None = Field(
        default=None, max_length=250, examples=["Друг з університету"]
    )


class ContactModel(ContactBase):
    """Тіло запиту для створення контакту та для повного оновлення (PUT)."""


class ContactResponse(ContactBase):
    """Контакт у відповіді API."""

    id: int
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------- користувачі --
class UserCreate(BaseModel):
    """Тіло запиту на реєстрацію нового користувача."""

    username: str = Field(min_length=3, max_length=50, examples=["ivan"])
    email: EmailStr = Field(max_length=100, examples=["ivan.petrenko@example.com"])
    password: str = Field(min_length=6, max_length=128, examples=["SuperSecret1"])
    role: UserRole = Field(default=UserRole.USER, examples=["user"])


class User(BaseModel):
    """Публічне подання користувача; хеш пароля назовні не потрапляє."""

    id: int
    username: str
    email: EmailStr
    avatar: str | None = None
    confirmed: bool = False
    role: UserRole = UserRole.USER

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------ токени --
class Token(BaseModel):
    """Пара JWT-токенів, що повертається під час входу та оновлення."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Тіло запиту на оновлення пари токенів."""

    refresh_token: str


class RequestEmail(BaseModel):
    """Тіло запиту, у якому достатньо лише електронної адреси."""

    email: EmailStr


# --------------------------------------------------------- скидання пароля --
class PasswordResetRequest(BaseModel):
    """Тіло запиту на надсилання листа зі скиданням пароля."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Тіло запиту на встановлення нового пароля за токеном із листа."""

    token: str
    new_password: str = Field(min_length=6, max_length=128, examples=["NewSecret1"])

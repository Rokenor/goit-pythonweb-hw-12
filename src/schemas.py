from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------- контакти --
class ContactBase(BaseModel):
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
    id: int
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------- користувачі --
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, examples=["ivan"])
    email: EmailStr = Field(max_length=100, examples=["ivan.petrenko@example.com"])
    password: str = Field(min_length=6, max_length=128, examples=["SuperSecret1"])


class User(BaseModel):
    id: int
    username: str
    email: EmailStr
    avatar: str | None = None
    confirmed: bool = False

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RequestEmail(BaseModel):
    email: EmailStr

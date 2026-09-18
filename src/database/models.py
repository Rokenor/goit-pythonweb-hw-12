"""Декларативні моделі SQLAlchemy застосунку.

Модуль описує дві таблиці: :class:`User` — зареєстровані користувачі разом
з їхньою роллю, та :class:`Contact` — контакти, що завжди належать
конкретному користувачеві.
"""

from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовий клас для всіх декларативних моделей."""


class UserRole(str, Enum):
    """Ролі користувачів застосунку.

    :cvar USER: звичайний користувач — керує лише власними контактами.
    :cvar ADMIN: адміністратор — додатково може змінювати свій аватар.
    """

    USER = "user"
    ADMIN = "admin"


class User(Base):
    """Зареєстрований користувач застосунку.

    :ivar id: первинний ключ.
    :ivar username: унікальне ім'я користувача (логін).
    :ivar email: унікальна електронна адреса.
    :ivar hashed_password: bcrypt-хеш пароля; відкритий пароль не зберігається.
    :ivar avatar: URL аватара (Gravatar або Cloudinary).
    :ivar confirmed: чи підтверджена електронна адреса.
    :ivar role: роль користувача, див. :class:`UserRole`.
    :ivar created_at: час створення запису.
    :ivar contacts: контакти, що належать користувачеві.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    email: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="user_role"),
        default=UserRole.USER,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    contacts: Mapped[list["Contact"]] = relationship(
        "Contact", back_populates="user", cascade="all, delete-orphan"
    )


class Contact(Base):
    """Контакт у записнику користувача.

    :ivar id: первинний ключ.
    :ivar first_name: ім'я.
    :ivar last_name: прізвище.
    :ivar email: електронна адреса; унікальна в межах одного власника.
    :ivar phone: номер телефону.
    :ivar birthday: дата народження.
    :ivar additional_data: довільна додаткова інформація.
    :ivar created_at: час створення запису.
    :ivar updated_at: час останнього оновлення запису.
    :ivar user_id: ідентифікатор власника.
    :ivar user: власник контакту.
    """

    __tablename__ = "contacts"
    # email унікальний у межах одного користувача, а не глобально
    __table_args__ = (
        UniqueConstraint("email", "user_id", name="uq_contacts_email_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(25), nullable=False)
    birthday: Mapped[date] = mapped_column(Date, nullable=False)
    additional_data: Mapped[str | None] = mapped_column(String(250), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user: Mapped["User"] = relationship("User", back_populates="contacts")

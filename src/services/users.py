"""Бізнес-логіка роботи з користувачами.

Сервіс тонкий: він доповнює репозиторій тим, чого тому знати не варто, —
отриманням аватара з Gravatar і скиданням Redis-кешу після кожної зміни
користувача.
"""

import logging

from libgravatar import Gravatar
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.repository.users import UserRepository
from src.schemas import UserCreate
from src.services.cache import invalidate_user_cache

logger = logging.getLogger(__name__)


class UserService:
    """Операції над користувачами разом з інвалідацією кешу."""

    def __init__(self, db: AsyncSession):
        """
        :param db: асинхронна сесія SQLAlchemy.
        :type db: AsyncSession
        """
        self.repository = UserRepository(db)

    async def create_user(self, body: UserCreate, hashed_password: str) -> User:
        """Створює користувача, підтягуючи аватар із Gravatar.

        :param body: дані реєстрації.
        :type body: UserCreate
        :param hashed_password: bcrypt-хеш пароля.
        :type hashed_password: str
        :return: збережений користувач.
        :rtype: User
        """
        avatar = None
        try:
            avatar = Gravatar(str(body.email)).get_image()
        except Exception as err:  # gravatar недоступний — не критично
            logger.warning("Gravatar unavailable: %s", err)
        return await self.repository.create_user(body, hashed_password, avatar)

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Повертає користувача за ідентифікатором.

        :param user_id: ідентифікатор користувача.
        :type user_id: int
        :return: користувач або ``None``.
        :rtype: User | None
        """
        return await self.repository.get_user_by_id(user_id)

    async def get_user_by_username(self, username: str) -> User | None:
        """Повертає користувача за іменем.

        :param username: ім'я користувача.
        :type username: str
        :return: користувач або ``None``.
        :rtype: User | None
        """
        return await self.repository.get_user_by_username(username)

    async def get_user_by_email(self, email: str) -> User | None:
        """Повертає користувача за електронною адресою.

        :param email: електронна адреса.
        :type email: str
        :return: користувач або ``None``.
        :rtype: User | None
        """
        return await self.repository.get_user_by_email(email)

    async def confirmed_email(self, email: str) -> User | None:
        """Підтверджує електронну адресу та скидає кеш користувача.

        :param email: електронна адреса.
        :type email: str
        :return: оновлений користувач або ``None``.
        :rtype: User | None
        """
        user = await self.repository.confirmed_email(email)
        await invalidate_user_cache(user.username if user else None)
        return user

    async def update_avatar_url(self, email: str, url: str) -> User | None:
        """Оновлює аватар і скидає кеш користувача.

        :param email: електронна адреса.
        :type email: str
        :param url: нове посилання на зображення.
        :type url: str
        :return: оновлений користувач або ``None``.
        :rtype: User | None
        """
        user = await self.repository.update_avatar_url(email, url)
        await invalidate_user_cache(user.username if user else None)
        return user

    async def update_password(self, email: str, hashed_password: str) -> User | None:
        """Зберігає новий пароль і скидає кеш користувача.

        :param email: електронна адреса.
        :type email: str
        :param hashed_password: новий bcrypt-хеш пароля.
        :type hashed_password: str
        :return: оновлений користувач або ``None``.
        :rtype: User | None
        """
        user = await self.repository.update_password(email, hashed_password)
        await invalidate_user_cache(user.username if user else None)
        return user

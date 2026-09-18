"""Доступ до таблиці користувачів."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.schemas import UserCreate


class UserRepository:
    """CRUD-операції над користувачами."""

    def __init__(self, session: AsyncSession):
        """
        :param session: асинхронна сесія SQLAlchemy.
        :type session: AsyncSession
        """
        self.db = session

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Знаходить користувача за первинним ключем.

        :param user_id: ідентифікатор користувача.
        :type user_id: int
        :return: користувач або ``None``.
        :rtype: User | None
        """
        stmt = select(User).filter_by(id=user_id)
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User | None:
        """Знаходить користувача за іменем без урахування регістру.

        :param username: ім'я користувача.
        :type username: str
        :return: користувач або ``None``.
        :rtype: User | None
        """
        stmt = select(User).filter(func.lower(User.username) == username.lower())
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Знаходить користувача за електронною адресою без урахування регістру.

        :param email: електронна адреса.
        :type email: str
        :return: користувач або ``None``.
        :rtype: User | None
        """
        stmt = select(User).filter(func.lower(User.email) == email.lower())
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def create_user(
        self, body: UserCreate, hashed_password: str, avatar: str | None = None
    ) -> User:
        """Створює нового користувача.

        :param body: дані реєстрації.
        :type body: UserCreate
        :param hashed_password: заздалегідь обчислений bcrypt-хеш пароля.
        :type hashed_password: str
        :param avatar: URL аватара (зазвичай Gravatar).
        :type avatar: str | None
        :return: збережений користувач.
        :rtype: User
        """
        user = User(
            username=body.username,
            email=str(body.email),
            hashed_password=hashed_password,
            avatar=avatar,
            role=body.role,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def confirmed_email(self, email: str) -> User | None:
        """Позначає електронну адресу користувача як підтверджену.

        :param email: електронна адреса.
        :type email: str
        :return: оновлений користувач або ``None``, якщо його не знайдено.
        :rtype: User | None
        """
        user = await self.get_user_by_email(email)
        if user:
            user.confirmed = True
            await self.db.commit()
            await self.db.refresh(user)
        return user

    async def update_avatar_url(self, email: str, url: str) -> User | None:
        """Замінює URL аватара користувача.

        :param email: електронна адреса.
        :type email: str
        :param url: нове посилання на зображення.
        :type url: str
        :return: оновлений користувач або ``None``, якщо його не знайдено.
        :rtype: User | None
        """
        user = await self.get_user_by_email(email)
        if user:
            user.avatar = url
            await self.db.commit()
            await self.db.refresh(user)
        return user

    async def update_password(self, email: str, hashed_password: str) -> User | None:
        """Зберігає новий хеш пароля користувача.

        :param email: електронна адреса.
        :type email: str
        :param hashed_password: новий bcrypt-хеш.
        :type hashed_password: str
        :return: оновлений користувач або ``None``, якщо його не знайдено.
        :rtype: User | None
        """
        user = await self.get_user_by_email(email)
        if user:
            user.hashed_password = hashed_password
            await self.db.commit()
            await self.db.refresh(user)
        return user

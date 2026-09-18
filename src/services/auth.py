"""Аутентифікація, авторизація та робота з JWT-токенами.

Модуль містить:

* :class:`Hash` — хешування й перевірку паролів (bcrypt);
* створення й розбір чотирьох типів JWT: ``access``, ``refresh``, ``email``
  та ``password_reset``;
* залежність :func:`get_current_user`, яка бере користувача з Redis-кешу
  й лише за потреби звертається до бази даних;
* залежність :func:`get_current_admin_user` для маршрутів, доступних
  винятково адміністраторам.
"""

from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.conf.config import settings
from src.database.db import get_db
from src.database.models import User, UserRole
from src.services.cache import cache_user, get_cached_user
from src.services.users import UserService

#: Значення claim ``token_type`` для кожного призначення токена.
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"
TOKEN_TYPE_EMAIL = "email"
TOKEN_TYPE_PASSWORD_RESET = "password_reset"


class Hash:
    """Хешування та перевірка паролів (bcrypt) — відкритий пароль не зберігається."""

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Перевіряє, чи відповідає відкритий пароль збереженому хешу.

        :param plain_password: пароль у відкритому вигляді.
        :type plain_password: str
        :param hashed_password: bcrypt-хеш із бази даних.
        :type hashed_password: str
        :return: ``True``, якщо пароль правильний.
        :rtype: bool
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Обчислює bcrypt-хеш пароля.

        :param password: пароль у відкритому вигляді.
        :type password: str
        :return: хеш, придатний для збереження в базі.
        :rtype: str
        """
        return self.pwd_context.hash(password)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _create_token(data: dict, token_type: str, expires_seconds: int) -> str:
    """Кодує JWT із заданим призначенням і часом життя.

    :param data: корисне навантаження (щонайменше ``sub``).
    :type data: dict
    :param token_type: призначення токена, напр. ``"access"``.
    :type token_type: str
    :param expires_seconds: час життя токена в секундах.
    :type expires_seconds: int
    :return: підписаний JWT.
    :rtype: str
    """
    to_encode = data.copy()
    now = datetime.now(UTC)
    to_encode.update(
        {
            "iat": now,
            "exp": now + timedelta(seconds=expires_seconds),
            "token_type": token_type,
        }
    )
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _decode_token(token: str, expected_type: str) -> dict:
    """Перевіряє підпис, термін дії та призначення токена.

    :param token: JWT у вигляді рядка.
    :type token: str
    :param expected_type: очікуване значення claim ``token_type``.
    :type expected_type: str
    :raises JWTError: якщо токен недійсний або має інше призначення.
    :return: розкодоване корисне навантаження.
    :rtype: dict
    """
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("token_type") != expected_type:
        raise JWTError(f"Expected {expected_type} token")
    return payload


async def create_access_token(data: dict, expires_delta: int | None = None) -> str:
    """Створює короткоживучий ``access_token``.

    :param data: корисне навантаження; ``sub`` має містити ім'я користувача.
    :type data: dict
    :param expires_delta: час життя в секундах; за замовчуванням —
        ``JWT_EXPIRATION_SECONDS``.
    :type expires_delta: int | None
    :return: підписаний JWT доступу.
    :rtype: str
    """
    return _create_token(
        data, TOKEN_TYPE_ACCESS, expires_delta or settings.JWT_EXPIRATION_SECONDS
    )


async def create_refresh_token(data: dict, expires_delta: int | None = None) -> str:
    """Створює довгоживучий ``refresh_token``.

    :param data: корисне навантаження; ``sub`` має містити ім'я користувача.
    :type data: dict
    :param expires_delta: час життя в секундах; за замовчуванням —
        ``JWT_REFRESH_EXPIRATION_SECONDS``.
    :type expires_delta: int | None
    :return: підписаний JWT оновлення.
    :rtype: str
    """
    return _create_token(
        data,
        TOKEN_TYPE_REFRESH,
        expires_delta or settings.JWT_REFRESH_EXPIRATION_SECONDS,
    )


async def decode_refresh_token(token: str) -> str:
    """Розбирає ``refresh_token`` і повертає ім'я користувача.

    :param token: refresh-токен.
    :type token: str
    :raises HTTPException: 401, якщо токен недійсний, прострочений або
        насправді є токеном іншого типу.
    :return: значення claim ``sub``.
    :rtype: str
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недійсний refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = _decode_token(token, TOKEN_TYPE_REFRESH)
    except JWTError:
        raise credentials_exception
    username = payload.get("sub")
    if username is None:
        raise credentials_exception
    return username


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """Повертає користувача, якому належить ``access_token``.

    Спершу перевіряється Redis-кеш; звернення до бази відбувається лише
    тоді, коли в кеші користувача немає (або кеш недоступний). Отриманого
    з бази користувача одразу покладено в кеш.

    :param token: значення заголовка ``Authorization: Bearer <token>``.
    :type token: str
    :param db: сесія бази даних.
    :type db: AsyncSession
    :raises HTTPException: 401, якщо токен недійсний або користувача немає.
    :return: поточний користувач.
    :rtype: User
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = _decode_token(token, TOKEN_TYPE_ACCESS)
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    cached = await get_cached_user(username)
    if cached is not None:
        return cached

    user = await UserService(db).get_user_by_username(username)
    if user is None:
        raise credentials_exception
    await cache_user(user)
    return user


async def get_current_admin_user(user: User = Depends(get_current_user)) -> User:
    """Пропускає далі лише користувачів із роллю ``admin``.

    :param user: поточний користувач.
    :type user: User
    :raises HTTPException: 403, якщо роль користувача не ``admin``.
    :return: поточний користувач-адміністратор.
    :rtype: User
    """
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостатньо прав доступу",
        )
    return user


def create_email_token(data: dict) -> str:
    """Створює токен для підтвердження електронної пошти (діє 7 днів).

    :param data: корисне навантаження; ``sub`` має містити email.
    :type data: dict
    :return: підписаний JWT підтвердження пошти.
    :rtype: str
    """
    return _create_token(data, TOKEN_TYPE_EMAIL, 7 * 24 * 3600)


async def get_email_from_token(token: str) -> str:
    """Дістає електронну адресу з токена підтвердження пошти.

    :param token: токен із листа.
    :type token: str
    :raises HTTPException: 422, якщо токен недійсний.
    :return: електронна адреса.
    :rtype: str
    """
    try:
        payload = _decode_token(token, TOKEN_TYPE_EMAIL)
        return payload["sub"]
    except (JWTError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Невірний токен для перевірки електронної пошти",
        )


def create_password_reset_token(email: str) -> str:
    """Створює одноразовий токен для скидання пароля.

    Час життя визначає ``PASSWORD_RESET_EXPIRATION_SECONDS`` (типово година),
    щоб посилання з листа швидко втрачало силу.

    :param email: електронна адреса користувача.
    :type email: str
    :return: підписаний JWT скидання пароля.
    :rtype: str
    """
    return _create_token(
        {"sub": email},
        TOKEN_TYPE_PASSWORD_RESET,
        settings.PASSWORD_RESET_EXPIRATION_SECONDS,
    )


async def get_email_from_reset_token(token: str) -> str:
    """Дістає електронну адресу з токена скидання пароля.

    :param token: токен із листа про скидання пароля.
    :type token: str
    :raises HTTPException: 422, якщо токен недійсний або прострочений.
    :return: електронна адреса.
    :rtype: str
    """
    try:
        payload = _decode_token(token, TOKEN_TYPE_PASSWORD_RESET)
        return payload["sub"]
    except (JWTError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Невірний або прострочений токен для скидання пароля",
        )

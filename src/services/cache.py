"""Кешування поточного користувача в Redis.

Мета — щоб залежність :func:`src.services.auth.get_current_user` на кожен
запит не ходила в базу даних. Користувач серіалізується в JSON і зберігається
під ключем ``user:<username>`` з обмеженим часом життя
(``USER_CACHE_TTL``), тож навіть у разі пропущеної інвалідації дані
самостійно застаріють.

Для безпеки в кеш потрапляють лише ті поля, які застосунок віддає назовні,
— хеш пароля там не зберігається. Будь-яка зміна користувача (підтвердження
пошти, зміна аватара чи пароля) супроводжується викликом
:func:`invalidate_user_cache`.
"""

import json
import logging
from datetime import datetime

import redis.asyncio as redis_asyncio
from redis.exceptions import RedisError

from src.conf.config import settings
from src.database.models import User, UserRole

logger = logging.getLogger(__name__)

CACHED_FIELDS = ("id", "username", "email", "avatar", "confirmed", "role", "created_at")

_redis_client: redis_asyncio.Redis | None = None


def get_redis() -> redis_asyncio.Redis | None:
    """Повертає спільний клієнт Redis або ``None``, якщо кеш вимкнено.

    Клієнт створюється один раз і далі перевикористовується.

    :return: клієнт Redis або ``None``, якщо ``REDIS_ENABLED`` вимкнено.
    :rtype: redis.asyncio.Redis | None
    """
    global _redis_client
    if not settings.REDIS_ENABLED:
        return None
    if _redis_client is None:
        _redis_client = redis_asyncio.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
        )
    return _redis_client


def _key(username: str) -> str:
    """Формує ключ кешу для користувача.

    :param username: ім'я користувача.
    :type username: str
    :return: ключ у просторі імен ``user:``.
    :rtype: str
    """
    return f"user:{username.lower()}"


def _serialize(user: User) -> str:
    """Перетворює користувача на JSON-рядок для збереження в кеші.

    :param user: користувач із бази даних.
    :type user: User
    :return: JSON-подання дозволених полів.
    :rtype: str
    """
    payload = {}
    for field in CACHED_FIELDS:
        value = getattr(user, field, None)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, UserRole):
            value = value.value
        payload[field] = value
    return json.dumps(payload)


def _deserialize(raw: str) -> User:
    """Відновлює об'єкт :class:`~src.database.models.User` з кешу.

    Повернений екземпляр не прив'язаний до сесії SQLAlchemy — це звичайний
    об'єкт у пам'яті, придатний лише для читання.

    :param raw: JSON-рядок із кешу.
    :type raw: str
    :return: користувач, відновлений із кешу.
    :rtype: User
    """
    data = json.loads(raw)
    created_at = data.get("created_at")
    return User(
        id=data["id"],
        username=data["username"],
        email=data["email"],
        avatar=data.get("avatar"),
        confirmed=data.get("confirmed", False),
        role=UserRole(data.get("role", UserRole.USER.value)),
        created_at=datetime.fromisoformat(created_at) if created_at else None,
    )


async def get_cached_user(username: str) -> User | None:
    """Дістає користувача з кешу за іменем.

    Помилки Redis не поширюються далі: якщо кеш недоступний, застосунок
    просто працює з базою даних.

    :param username: ім'я користувача.
    :type username: str
    :return: користувач із кешу або ``None``, якщо його там немає.
    :rtype: User | None
    """
    client = get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(_key(username))
    except RedisError as err:  # кеш недоступний — не критично
        logger.warning("Redis unavailable on read: %s", err)
        return None
    if not raw:
        return None
    try:
        return _deserialize(raw)
    except (ValueError, KeyError) as err:  # пошкоджений запис
        logger.warning("Corrupted cache entry for %s: %s", username, err)
        await invalidate_user_cache(username)
        return None


async def cache_user(user: User) -> None:
    """Зберігає користувача в кеші на ``USER_CACHE_TTL`` секунд.

    :param user: користувач, якого треба покласти в кеш.
    :type user: User
    :return: ``None``
    """
    client = get_redis()
    if client is None:
        return
    try:
        await client.set(_key(user.username), _serialize(user), ex=settings.USER_CACHE_TTL)
    except RedisError as err:
        logger.warning("Redis unavailable on write: %s", err)


async def invalidate_user_cache(username: str | None) -> None:
    """Видаляє користувача з кешу.

    Викликається щоразу, коли дані користувача змінюються, щоб наступний
    запит прочитав актуальний стан із бази.

    :param username: ім'я користувача; ``None`` ігнорується.
    :type username: str | None
    :return: ``None``
    """
    if not username:
        return
    client = get_redis()
    if client is None:
        return
    try:
        await client.delete(_key(username))
    except RedisError as err:
        logger.warning("Redis unavailable on delete: %s", err)


async def close_redis() -> None:
    """Закриває з'єднання з Redis (використовується під час зупинки застосунку)."""
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except RedisError as err:
            logger.warning("Redis close failed: %s", err)
        _redis_client = None

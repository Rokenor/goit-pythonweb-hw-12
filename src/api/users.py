"""Маршрути для роботи з поточним користувачем."""

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.conf.config import settings
from src.database.db import get_db
from src.database.models import User as UserModel
from src.schemas import User
from src.services.auth import get_current_admin_user, get_current_user
from src.services.rate_limit import limiter
from src.services.upload_file import UploadFileService
from src.services.users import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=User,
    description=f"Не більше ніж {settings.USER_ME_RATE_LIMIT} запитів",
)
@limiter.limit(settings.USER_ME_RATE_LIMIT)
async def me(request: Request, user: UserModel = Depends(get_current_user)):
    """Повертає дані поточного користувача.

    Маршрут обмежений за кількістю запитів, а сам користувач береться
    з Redis-кешу, тож звернення до бази тут здебільшого не відбувається.

    :param request: HTTP-запит (потрібен лімітеру запитів).
    :type request: Request
    :param user: поточний користувач із залежності.
    :type user: UserModel
    :return: дані користувача.
    :rtype: User
    """
    return user


@router.patch(
    "/avatar",
    response_model=User,
    description="Доступно лише користувачам з роллю admin",
)
async def update_avatar_user(
    file: UploadFile = File(),
    user: UserModel = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Замінює типовий аватар користувача власним зображенням.

    Маршрут доступний лише адміністраторам: звичайні користувачі
    залишаються з аватаром за замовчуванням (Gravatar).

    :param file: завантажений файл зображення.
    :type file: UploadFile
    :param user: поточний користувач; має роль ``admin``.
    :type user: UserModel
    :param db: сесія бази даних.
    :type db: AsyncSession
    :raises HTTPException: 403, якщо роль користувача не ``admin``.
    :return: користувач з оновленим аватаром.
    :rtype: User
    """
    avatar_url = UploadFileService(
        settings.CLD_NAME, settings.CLD_API_KEY, settings.CLD_API_SECRET
    ).upload_file(file, user.username)

    return await UserService(db).update_avatar_url(user.email, avatar_url)

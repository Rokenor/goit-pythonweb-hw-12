from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.conf.config import settings
from src.database.db import get_db
from src.database.models import User as UserModel
from src.schemas import User
from src.services.auth import get_current_user
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
    """Дані поточного користувача. Маршрут обмежений за кількістю запитів."""
    return user


@router.patch("/avatar", response_model=User)
async def update_avatar_user(
    file: UploadFile = File(),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Оновлення аватара поточного користувача через Cloudinary."""
    avatar_url = UploadFileService(
        settings.CLD_NAME, settings.CLD_API_KEY, settings.CLD_API_SECRET
    ).upload_file(file, user.username)

    return await UserService(db).update_avatar_url(user.email, avatar_url)

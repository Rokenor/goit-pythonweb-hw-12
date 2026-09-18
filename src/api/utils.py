"""Службові маршрути застосунку."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["utils"])


@router.get("/healthchecker")
async def healthchecker(db: AsyncSession = Depends(get_db)):
    """Перевіряє, що застосунок піднявся і база даних відповідає.

    :param db: сесія бази даних.
    :type db: AsyncSession
    :raises HTTPException: 500, якщо база недоступна або налаштована хибно.
    :return: вітальне повідомлення.
    :rtype: dict
    """
    try:
        result = await db.execute(text("SELECT 1"))
        result = result.scalar_one_or_none()

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database is not configured correctly",
            )
        return {"message": "Welcome to FastAPI!"}
    except HTTPException:
        raise
    except Exception as err:
        logger.error("Healthcheck failed: %s", err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error connecting to the database",
        )

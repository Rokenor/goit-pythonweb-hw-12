"""Надсилання транзакційних листів.

Використовується два шаблони: підтвердження електронної пошти після
реєстрації та лист зі скиданням пароля.
"""

import logging
from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors
from pydantic import EmailStr

from src.conf.config import settings
from src.services.auth import create_email_token, create_password_reset_token

logger = logging.getLogger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=settings.VALIDATE_CERTS,
    TEMPLATE_FOLDER=Path(__file__).parent / "templates",
)


async def send_email(email: EmailStr, username: str, host: str) -> None:
    """Надсилає лист із посиланням для підтвердження електронної пошти.

    :param email: адреса отримувача.
    :type email: EmailStr
    :param username: ім'я користувача для звертання в листі.
    :type username: str
    :param host: базовий URL застосунку, з якого будується посилання.
    :type host: str
    :return: ``None``
    """
    try:
        token_verification = create_email_token({"sub": str(email)})
        message = MessageSchema(
            subject="Підтвердження електронної пошти — Contacts API",
            recipients=[email],
            template_body={
                "host": host,
                "username": username,
                "token": token_verification,
            },
            subtype=MessageType.html,
        )
        await FastMail(conf).send_message(message, template_name="verify_email.html")
    except ConnectionErrors as err:
        logger.error("Failed to send verification email: %s", err)


async def send_reset_password_email(
    email: EmailStr, username: str, host: str
) -> None:
    """Надсилає лист із токеном для скидання пароля.

    Токен генерується тут і ніде не зберігається: його дійсність
    підтверджує лише підпис JWT і термін дії.

    :param email: адреса отримувача.
    :type email: EmailStr
    :param username: ім'я користувача для звертання в листі.
    :type username: str
    :param host: базовий URL застосунку, з якого будується посилання.
    :type host: str
    :return: ``None``
    """
    try:
        reset_token = create_password_reset_token(str(email))
        message = MessageSchema(
            subject="Скидання пароля — Contacts API",
            recipients=[email],
            template_body={
                "host": host,
                "username": username,
                "token": reset_token,
                "ttl_hours": max(
                    1, settings.PASSWORD_RESET_EXPIRATION_SECONDS // 3600
                ),
            },
            subtype=MessageType.html,
        )
        await FastMail(conf).send_message(message, template_name="reset_password.html")
    except ConnectionErrors as err:
        logger.error("Failed to send password reset email: %s", err)

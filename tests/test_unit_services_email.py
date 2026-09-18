"""Модульні тести надсилання листів (SMTP не використовується)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi_mail.errors import ConnectionErrors

from src.services.auth import get_email_from_reset_token, get_email_from_token
from src.services.email import send_email, send_reset_password_email


@pytest.fixture
def fast_mail():
    with patch("src.services.email.FastMail") as fast_mail:
        fast_mail.return_value.send_message = AsyncMock()
        yield fast_mail


async def test_send_email_uses_verification_template(fast_mail):
    await send_email("deadpool@example.com", "deadpool", "http://testserver/")

    send_message = fast_mail.return_value.send_message
    send_message.assert_awaited_once()
    message, kwargs = send_message.await_args.args[0], send_message.await_args.kwargs
    assert kwargs["template_name"] == "verify_email.html"
    assert [str(r.email) for r in message.recipients] == ["deadpool@example.com"]
    assert message.template_body["username"] == "deadpool"
    token = message.template_body["token"]
    assert await get_email_from_token(token) == "deadpool@example.com"


async def test_send_reset_password_email_uses_reset_template(fast_mail):
    await send_reset_password_email("deadpool@example.com", "deadpool", "http://x/")

    send_message = fast_mail.return_value.send_message
    message, kwargs = send_message.await_args.args[0], send_message.await_args.kwargs
    assert kwargs["template_name"] == "reset_password.html"
    token = message.template_body["token"]
    assert await get_email_from_reset_token(token) == "deadpool@example.com"
    assert message.template_body["ttl_hours"] >= 1


async def test_send_email_swallows_connection_errors(fast_mail):
    fast_mail.return_value.send_message = AsyncMock(
        side_effect=ConnectionErrors("smtp is down")
    )

    await send_email("deadpool@example.com", "deadpool", "http://x/")


async def test_send_reset_password_email_swallows_connection_errors(fast_mail):
    fast_mail.return_value.send_message = AsyncMock(
        side_effect=ConnectionErrors("smtp is down")
    )

    await send_reset_password_email("deadpool@example.com", "deadpool", "http://x/")

"""Інтеграційні тести маршрутів аутентифікації."""

from unittest.mock import Mock

import pytest
from sqlalchemy import select

from src.database.models import User
from src.services.auth import (
    create_email_token,
    create_password_reset_token,
    create_refresh_token,
)
from tests.conftest import TestingSessionLocal, test_user

user_data = {
    "username": "agent007",
    "email": "agent007@example.com",
    "password": "12345678",
}


async def _get_user(email: str) -> User | None:
    async with TestingSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()


async def _confirm(email: str) -> None:
    async with TestingSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.confirmed = True
            await session.commit()


# --------------------------------------------------------------- реєстрація --
def test_signup(client, monkeypatch):
    monkeypatch.setattr("src.api.auth.send_email", Mock())
    response = client.post("api/auth/register", json=user_data)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert data["role"] == "user"
    assert "hashed_password" not in data
    assert "avatar" in data


def test_repeat_signup_email(client, monkeypatch):
    monkeypatch.setattr("src.api.auth.send_email", Mock())
    response = client.post("api/auth/register", json=user_data)

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "Користувач з таким email вже існує"


def test_repeat_signup_username(client, monkeypatch):
    monkeypatch.setattr("src.api.auth.send_email", Mock())
    response = client.post(
        "api/auth/register", json={**user_data, "email": "other@example.com"}
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "Користувач з таким іменем вже існує"


def test_signup_admin_role(client, monkeypatch):
    monkeypatch.setattr("src.api.auth.send_email", Mock())
    response = client.post(
        "api/auth/register",
        json={
            "username": "bigboss",
            "email": "bigboss@example.com",
            "password": "12345678",
            "role": "admin",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["role"] == "admin"


# --------------------------------------------------------------------- вхід --
def test_not_confirmed_login(client):
    response = client.post(
        "api/auth/login",
        data={"username": user_data["username"], "password": user_data["password"]},
    )

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Електронна адреса не підтверджена"


@pytest.mark.asyncio
async def test_login_returns_token_pair(client):
    await _confirm(user_data["email"])

    response = client.post(
        "api/auth/login",
        data={"username": user_data["username"], "password": user_data["password"]},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["access_token"] != data["refresh_token"]
    assert data["token_type"] == "bearer"


def test_wrong_password_login(client):
    response = client.post(
        "api/auth/login",
        data={"username": user_data["username"], "password": "password"},
    )

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Неправильний логін або пароль"


def test_wrong_username_login(client):
    response = client.post(
        "api/auth/login",
        data={"username": "no-such-user", "password": user_data["password"]},
    )

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Неправильний логін або пароль"


def test_validation_error_login(client):
    response = client.post("api/auth/login", data={"password": user_data["password"]})

    assert response.status_code == 422, response.text
    assert "detail" in response.json()


# ---------------------------------------------------------- оновлення токенів --
def test_refresh_token_returns_new_pair(client, get_refresh_token):
    response = client.post(
        "api/auth/refresh_token", json={"refresh_token": get_refresh_token}
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]


def test_refresh_token_rejects_access_token(client, get_token):
    response = client.post("api/auth/refresh_token", json={"refresh_token": get_token})

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Недійсний refresh token"


def test_refresh_token_rejects_garbage(client):
    response = client.post("api/auth/refresh_token", json={"refresh_token": "junk"})

    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_refresh_token_of_deleted_user(client):
    token = await create_refresh_token({"sub": "ghost"})
    response = client.post("api/auth/refresh_token", json={"refresh_token": token})

    assert response.status_code == 401, response.text


# ------------------------------------------------------- підтвердження пошти --
@pytest.mark.asyncio
async def test_confirm_email(client, monkeypatch):
    monkeypatch.setattr("src.api.auth.send_email", Mock())
    client.post(
        "api/auth/register",
        json={
            "username": "fresh",
            "email": "fresh@example.com",
            "password": "12345678",
        },
    )
    token = create_email_token({"sub": "fresh@example.com"})

    response = client.get(f"api/auth/confirmed_email/{token}")
    assert response.status_code == 200, response.text
    assert response.json()["message"] == "Електронну пошту підтверджено"

    repeated = client.get(f"api/auth/confirmed_email/{token}")
    assert repeated.json()["message"] == "Ваша електронна пошта вже підтверджена"


@pytest.mark.asyncio
async def test_confirm_email_unknown_user(client):
    token = create_email_token({"sub": "ghost@example.com"})
    response = client.get(f"api/auth/confirmed_email/{token}")

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Verification error"


def test_confirm_email_invalid_token(client):
    response = client.get("api/auth/confirmed_email/not-a-token")

    assert response.status_code == 422, response.text


def test_request_email_for_confirmed_user(client):
    response = client.post("api/auth/request_email", json={"email": test_user["email"]})

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "Ваша електронна пошта вже підтверджена"


def test_request_email_for_new_user(client, monkeypatch):
    mock_send_email = Mock()
    monkeypatch.setattr("src.api.auth.send_email", mock_send_email)
    client.post(
        "api/auth/register",
        json={
            "username": "pending",
            "email": "pending@example.com",
            "password": "12345678",
        },
    )

    response = client.post(
        "api/auth/request_email", json={"email": "pending@example.com"}
    )

    assert response.status_code == 200, response.text
    assert "Перевірте свою електронну пошту" in response.json()["message"]
    assert mock_send_email.call_count == 2  # реєстрація + повторний запит


def test_request_email_for_unknown_user(client):
    response = client.post("api/auth/request_email", json={"email": "ghost@example.com"})

    assert response.status_code == 200, response.text
    assert "Перевірте свою електронну пошту" in response.json()["message"]


# --------------------------------------------------------- скидання пароля --
def test_password_reset_request_sends_email(client, monkeypatch):
    mock_send = Mock()
    monkeypatch.setattr("src.api.auth.send_reset_password_email", mock_send)

    response = client.post(
        "api/auth/password_reset_request", json={"email": test_user["email"]}
    )

    assert response.status_code == 200, response.text
    assert "Якщо така електронна адреса" in response.json()["message"]
    mock_send.assert_called_once()


def test_password_reset_request_hides_unknown_email(client, monkeypatch):
    mock_send = Mock()
    monkeypatch.setattr("src.api.auth.send_reset_password_email", mock_send)

    response = client.post(
        "api/auth/password_reset_request", json={"email": "ghost@example.com"}
    )

    assert response.status_code == 200, response.text
    assert "Якщо така електронна адреса" in response.json()["message"]
    mock_send.assert_not_called()


def test_verify_reset_token(client):
    token = create_password_reset_token(user_data["email"])
    response = client.get(f"api/auth/reset_password/{token}")

    assert response.status_code == 200, response.text
    assert response.json()["email"] == user_data["email"]


def test_verify_reset_token_invalid(client):
    response = client.get("api/auth/reset_password/not-a-token")

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_reset_password_changes_password(client):
    token = create_password_reset_token(user_data["email"])
    old_hash = (await _get_user(user_data["email"])).hashed_password

    response = client.post(
        "api/auth/reset_password",
        json={"token": token, "new_password": "NewSecret1"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "Пароль успішно змінено"
    assert (await _get_user(user_data["email"])).hashed_password != old_hash

    login = client.post(
        "api/auth/login",
        data={"username": user_data["username"], "password": "NewSecret1"},
    )
    assert login.status_code == 200, login.text

    old_login = client.post(
        "api/auth/login",
        data={"username": user_data["username"], "password": user_data["password"]},
    )
    assert old_login.status_code == 401


def test_reset_password_with_invalid_token(client):
    response = client.post(
        "api/auth/reset_password",
        json={"token": "junk", "new_password": "NewSecret1"},
    )

    assert response.status_code == 422, response.text


def test_reset_password_for_unknown_user(client):
    token = create_password_reset_token("ghost@example.com")
    response = client.post(
        "api/auth/reset_password",
        json={"token": token, "new_password": "NewSecret1"},
    )

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Користувача не знайдено"


def test_reset_password_rejects_short_password(client):
    token = create_password_reset_token(test_user["email"])
    response = client.post(
        "api/auth/reset_password", json={"token": token, "new_password": "123"}
    )

    assert response.status_code == 422, response.text

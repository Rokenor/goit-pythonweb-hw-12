"""Інтеграційні тести маршрутів користувача, зокрема доступу за ролями."""

from unittest.mock import AsyncMock, patch

from src.database.models import User, UserRole
from tests.conftest import test_admin, test_user


def test_get_me(client, get_token):
    response = client.get(
        "api/users/me", headers={"Authorization": f"Bearer {get_token}"}
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]
    assert data["role"] == "user"
    assert "avatar" in data


def test_get_me_requires_token(client):
    response = client.get("api/users/me")

    assert response.status_code == 401, response.text


def test_get_me_rejects_invalid_token(client):
    response = client.get(
        "api/users/me", headers={"Authorization": "Bearer not-a-token"}
    )

    assert response.status_code == 401, response.text


@patch("src.services.upload_file.UploadFileService.upload_file")
def test_admin_can_update_avatar(mock_upload_file, client, get_admin_token):
    fake_url = "http://example.com/avatar.jpg"
    mock_upload_file.return_value = fake_url

    response = client.patch(
        "/api/users/avatar",
        headers={"Authorization": f"Bearer {get_admin_token}"},
        files={"file": ("avatar.jpg", b"fake image content", "image/jpeg")},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == test_admin["username"]
    assert data["avatar"] == fake_url
    mock_upload_file.assert_called_once()


@patch("src.services.upload_file.UploadFileService.upload_file")
def test_regular_user_cannot_update_avatar(mock_upload_file, client, get_token):
    response = client.patch(
        "/api/users/avatar",
        headers={"Authorization": f"Bearer {get_token}"},
        files={"file": ("avatar.jpg", b"fake image content", "image/jpeg")},
    )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Недостатньо прав доступу"
    mock_upload_file.assert_not_called()


def test_update_avatar_requires_token(client):
    response = client.patch(
        "/api/users/avatar",
        files={"file": ("avatar.jpg", b"fake image content", "image/jpeg")},
    )

    assert response.status_code == 401, response.text


def test_me_is_served_from_cache(client, get_token):
    """Коли користувач є в кеші, запит не має торкатися бази даних."""
    cached = User(
        id=999,
        username=test_user["username"],
        email="cached@example.com",
        avatar="https://cached/avatar.png",
        confirmed=True,
        role=UserRole.USER,
    )

    with (
        patch(
            "src.services.auth.get_cached_user", new=AsyncMock(return_value=cached)
        ),
        patch("src.services.auth.UserService") as user_service,
    ):
        response = client.get(
            "api/users/me", headers={"Authorization": f"Bearer {get_token}"}
        )

    assert response.status_code == 200, response.text
    assert response.json()["email"] == "cached@example.com"
    user_service.assert_not_called()

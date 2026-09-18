"""Інтеграційні тести CRUD-маршрутів контактів."""

from datetime import date, timedelta

import pytest

from tests.conftest import test_admin

contact_payload = {
    "first_name": "Іван",
    "last_name": "Петренко",
    "email": "ivan.petrenko@example.com",
    "phone": "+380501234567",
    "birthday": "1990-04-15",
    "additional_data": "Друг з університету",
}


@pytest.fixture
def auth_headers(get_token):
    return {"Authorization": f"Bearer {get_token}"}


@pytest.fixture
def admin_headers(get_admin_token):
    return {"Authorization": f"Bearer {get_admin_token}"}


def test_create_contact(client, auth_headers):
    response = client.post("api/contacts/", json=contact_payload, headers=auth_headers)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["first_name"] == contact_payload["first_name"]
    assert data["email"] == contact_payload["email"]
    assert "id" in data


def test_create_duplicate_contact(client, auth_headers):
    response = client.post("api/contacts/", json=contact_payload, headers=auth_headers)

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "Contact with this email already exists"


def test_create_contact_validation_error(client, auth_headers):
    response = client.post(
        "api/contacts/",
        json={**contact_payload, "email": "not-an-email"},
        headers=auth_headers,
    )

    assert response.status_code == 422, response.text


def test_create_contact_requires_auth(client):
    response = client.post("api/contacts/", json=contact_payload)

    assert response.status_code == 401, response.text


def test_read_contacts(client, auth_headers):
    response = client.get("api/contacts/", headers=auth_headers)

    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["email"] == contact_payload["email"]


def test_read_contacts_search(client, auth_headers):
    found = client.get("api/contacts/?first_name=Іва", headers=auth_headers)
    assert found.status_code == 200, found.text
    assert len(found.json()) == 1

    missing = client.get("api/contacts/?last_name=Шевченко", headers=auth_headers)
    assert missing.json() == []

    by_email = client.get("api/contacts/?email=petrenko", headers=auth_headers)
    assert len(by_email.json()) == 1


def test_read_contacts_pagination(client, auth_headers):
    response = client.get("api/contacts/?skip=1&limit=10", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert response.json() == []


def test_read_contacts_rejects_bad_pagination(client, auth_headers):
    response = client.get("api/contacts/?limit=0", headers=auth_headers)

    assert response.status_code == 422, response.text


def test_read_contact(client, auth_headers):
    contact_id = client.get("api/contacts/", headers=auth_headers).json()[0]["id"]

    response = client.get(f"api/contacts/{contact_id}", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert response.json()["id"] == contact_id


def test_read_contact_not_found(client, auth_headers):
    response = client.get("api/contacts/9999", headers=auth_headers)

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Contact not found"


def test_contacts_are_isolated_per_user(client, auth_headers, admin_headers):
    contact_id = client.get("api/contacts/", headers=auth_headers).json()[0]["id"]

    assert client.get("api/contacts/", headers=admin_headers).json() == []
    assert client.get(f"api/contacts/{contact_id}", headers=admin_headers).status_code == 404


def test_update_contact(client, auth_headers):
    contact_id = client.get("api/contacts/", headers=auth_headers).json()[0]["id"]

    response = client.put(
        f"api/contacts/{contact_id}",
        json={**contact_payload, "first_name": "Оновлений"},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["first_name"] == "Оновлений"


def test_update_contact_not_found(client, auth_headers):
    response = client.put(
        "api/contacts/9999", json=contact_payload, headers=auth_headers
    )

    assert response.status_code == 404, response.text


def test_update_contact_email_conflict(client, auth_headers):
    first_id = client.get("api/contacts/", headers=auth_headers).json()[0]["id"]
    client.post(
        "api/contacts/",
        json={**contact_payload, "email": "second@example.com"},
        headers=auth_headers,
    )

    response = client.put(
        f"api/contacts/{first_id}",
        json={**contact_payload, "email": "second@example.com"},
        headers=auth_headers,
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "Contact with this email already exists"


def test_upcoming_birthdays(client, auth_headers):
    soon = date.today() + timedelta(days=3)
    client.post(
        "api/contacts/",
        json={
            **contact_payload,
            "email": "birthday@example.com",
            "birthday": soon.replace(year=1985).isoformat(),
        },
        headers=auth_headers,
    )

    response = client.get("api/contacts/birthdays", headers=auth_headers)

    assert response.status_code == 200, response.text
    emails = [contact["email"] for contact in response.json()]
    assert "birthday@example.com" in emails


def test_upcoming_birthdays_narrow_window(client, auth_headers):
    response = client.get("api/contacts/birthdays?days=1", headers=auth_headers)

    assert response.status_code == 200, response.text
    emails = [contact["email"] for contact in response.json()]
    assert "birthday@example.com" not in emails


def test_delete_contact(client, auth_headers):
    contacts = client.get("api/contacts/", headers=auth_headers).json()
    contact_id = contacts[-1]["id"]

    response = client.delete(f"api/contacts/{contact_id}", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert response.json()["id"] == contact_id
    assert client.get(f"api/contacts/{contact_id}", headers=auth_headers).status_code == 404


def test_delete_contact_not_found(client, auth_headers):
    response = client.delete("api/contacts/9999", headers=auth_headers)

    assert response.status_code == 404, response.text

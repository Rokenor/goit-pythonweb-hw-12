"""Модульні тести налаштувань застосунку в :mod:`main`."""

import json
from unittest.mock import AsyncMock, patch

from slowapi.errors import RateLimitExceeded

from main import app, lifespan, rate_limit_handler


async def test_rate_limit_handler_returns_429():
    limit = type("Limit", (), {"error_message": None, "limit": "10/minute"})()
    response = await rate_limit_handler(None, RateLimitExceeded(limit))

    assert response.status_code == 429
    assert "Перевищено ліміт запитів" in json.loads(response.body)["error"]


async def test_lifespan_closes_redis():
    with patch("main.close_redis", new=AsyncMock()) as close_redis:
        async with lifespan(app):
            pass

    close_redis.assert_awaited_once()


def test_routes_are_registered():
    paths = {route.path for route in app.routes}

    assert "/api/auth/login" in paths
    assert "/api/auth/refresh_token" in paths
    assert "/api/auth/reset_password" in paths
    assert "/api/users/me" in paths
    assert "/api/contacts/" in paths
    assert "/api/healthchecker" in paths

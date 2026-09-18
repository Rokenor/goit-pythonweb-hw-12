"""Точка входу застосунку Contacts API.

Модуль створює екземпляр FastAPI, налаштовує CORS, обробник перевищення
ліміту запитів, підключає маршрути та закриває з'єднання з Redis під час
зупинки сервера.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from src.api import auth, contacts, users, utils
from src.services.cache import close_redis
from src.services.rate_limit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Керує ресурсами, спільними для всього життєвого циклу застосунку.

    :param app: екземпляр застосунку.
    :type app: FastAPI
    """
    yield
    await close_redis()


app = FastAPI(
    title="Contacts API",
    description="REST API для зберігання та управління контактами",
    version="3.0.0",
    lifespan=lifespan,
)

# --- CORS -------------------------------------------------------------------
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Обмеження кількості запитів --------------------------------------------
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Повертає 429 замість стандартної помилки slowapi.

    :param request: запит, що перевищив ліміт.
    :type request: Request
    :param exc: виняток лімітера.
    :type exc: RateLimitExceeded
    :return: відповідь зі статусом 429.
    :rtype: JSONResponse
    """
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"error": "Перевищено ліміт запитів. Спробуйте пізніше."},
    )


# --- Маршрути ---------------------------------------------------------------
app.include_router(utils.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(contacts.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

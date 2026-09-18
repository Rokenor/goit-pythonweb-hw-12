# Contacts REST API

REST API для зберігання та управління контактами з аутентифікацією та авторизацією.
Стек: **FastAPI**, **SQLAlchemy 2.0** (async), **PostgreSQL**, **Alembic**, **Pydantic**,
**JWT** (python-jose), **passlib/bcrypt**, **fastapi-mail**, **Cloudinary**, **SlowAPI**.

## Запуск

### Усе в Docker Compose

```bash
cp .env.example .env     # заповніть POSTGRES_PASSWORD, JWT_SECRET, SMTP та Cloudinary
docker compose up -d     # PostgreSQL + API (міграції застосовуються автоматично)
```

### Локально (база в Docker)

```bash
poetry install --no-root
cp .env.example .env     # заповніть POSTGRES_PASSWORD, JWT_SECRET, SMTP та Cloudinary
docker compose up -d postgres
poetry run alembic upgrade head
poetry run uvicorn main:app --reload
```

Swagger-документація: http://127.0.0.1:8000/docs (також `/redoc`, `/openapi.json`).

## Ендпоінти

| Метод    | Шлях                                | Опис                                              |
| -------- | ----------------------------------- | ------------------------------------------------- |
| `POST`   | `/api/auth/register`                | Реєстрація → `201`; дублікат email → `409`        |
| `POST`   | `/api/auth/login`                   | Логін (form-data) → `access_token`; інакше `401`  |
| `GET`    | `/api/auth/confirmed_email/{token}` | Підтвердження електронної пошти                   |
| `POST`   | `/api/auth/request_email`           | Повторно надіслати лист із підтвердженням         |
| `GET`    | `/api/users/me` 🔒                  | Поточний користувач (обмежено `10/minute`)        |
| `PATCH`  | `/api/users/avatar` 🔒              | Оновити аватар (Cloudinary)                       |
| `POST`   | `/api/contacts/` 🔒                 | Створити контакт → `201`                          |
| `GET`    | `/api/contacts/` 🔒                 | Список контактів (пошук + пагінація)              |
| `GET`    | `/api/contacts/birthdays` 🔒        | Контакти з ДН на найближчі `days` днів (типово 7) |
| `GET`    | `/api/contacts/{id}` 🔒             | Контакт за ідентифікатором                        |
| `PUT`    | `/api/contacts/{id}` 🔒             | Оновити контакт                                   |
| `DELETE` | `/api/contacts/{id}` 🔒             | Видалити контакт                                  |
| `GET`    | `/api/healthchecker`                | Перевірка з'єднання з базою даних                 |

🔒 — потребує заголовка `Authorization: Bearer <access_token>`.

Пошук — `first_name`, `last_name`, `email` (частковий збіг без урахування регістру,
поєднуються через `AND`) плюс `skip`/`limit`. Дні народження порівнюються лише за
місяцем і днем, тому вікно працює через межу року (28.12 → 03.01).

Коди відповідей: некоректні дані → `422`, дублікат → `409`, неіснуючий або чужий
контакт → `404`, невалідний токен → `401`.

## Структура

Усі налаштування — у `.env` (шаблон у `.env.example`), у коді секретів немає.

```
main.py               # точка входу, CORS, rate limiting, роутери
Dockerfile            # образ застосунку
docker-compose.yml    # PostgreSQL + API
migrations/           # міграції Alembic
src/
├── api/              # роути (auth, users, contacts, healthchecker)
├── conf/config.py    # налаштування з .env
├── database/         # менеджер async-сесій та ORM-моделі
├── repository/       # шар доступу до даних (contacts, users)
├── services/         # бізнес-логіка, JWT, email, Cloudinary, rate limiter
└── schemas.py        # Pydantic-схеми
```

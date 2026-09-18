# Contacts REST API

REST API для зберігання та управління контактами з аутентифікацією, ролями
та кешуванням поточного користувача.
Стек: **FastAPI**, **SQLAlchemy 2.0** (async), **PostgreSQL**, **Redis**, **Alembic**,
**Pydantic**, **JWT** (python-jose), **passlib/bcrypt**, **fastapi-mail**,
**Cloudinary**, **SlowAPI**, **pytest** + **pytest-cov**, **Sphinx**.

## Запуск

### Усе в Docker Compose

```bash
cp .env.example .env     # заповніть POSTGRES_PASSWORD, JWT_SECRET, SMTP та Cloudinary
docker compose up -d     # PostgreSQL + Redis + API (міграції застосовуються автоматично)
```

### Локально (бази в Docker)

```bash
poetry install --no-root
cp .env.example .env     # заповніть POSTGRES_PASSWORD, JWT_SECRET, SMTP та Cloudinary
docker compose up -d postgres redis
poetry run alembic upgrade head
poetry run uvicorn main:app --reload
```

Swagger-документація: http://127.0.0.1:8000/docs (також `/redoc`, `/openapi.json`).

Якщо Redis недоступний, застосунок продовжує працювати — кожен запит просто йде
в базу. Кеш можна вимкнути й свідомо: `REDIS_ENABLED=False`.

## Ендпоінти

| Метод    | Шлях                                | Опис                                               |
| -------- | ----------------------------------- | -------------------------------------------------- |
| `POST`   | `/api/auth/register`                | Реєстрація → `201`; дублікат email → `409`         |
| `POST`   | `/api/auth/login`                   | Логін (form-data) → пара токенів; інакше `401`     |
| `POST`   | `/api/auth/refresh_token`           | Нова пара токенів за `refresh_token`               |
| `GET`    | `/api/auth/confirmed_email/{token}` | Підтвердження електронної пошти                    |
| `POST`   | `/api/auth/request_email`           | Повторно надіслати лист із підтвердженням          |
| `POST`   | `/api/auth/password_reset_request`  | Надіслати лист зі скиданням пароля                 |
| `GET`    | `/api/auth/reset_password/{token}`  | Перевірити токен скидання пароля                   |
| `POST`   | `/api/auth/reset_password`          | Установити новий пароль за токеном                 |
| `GET`    | `/api/users/me` 🔒                  | Поточний користувач (з кешу, обмежено `10/minute`) |
| `PATCH`  | `/api/users/avatar` 🔒              | Оновити аватар (Cloudinary) — **лише `admin`**     |
| `POST`   | `/api/contacts/` 🔒                 | Створити контакт → `201`                           |
| `GET`    | `/api/contacts/` 🔒                 | Список контактів (пошук + пагінація)               |
| `GET`    | `/api/contacts/birthdays` 🔒        | Контакти з ДН на найближчі `days` днів (типово 7)  |
| `GET`    | `/api/contacts/{id}` 🔒             | Контакт за ідентифікатором                         |
| `PUT`    | `/api/contacts/{id}` 🔒             | Оновити контакт                                    |
| `DELETE` | `/api/contacts/{id}` 🔒             | Видалити контакт                                   |
| `GET`    | `/api/healthchecker`                | Перевірка з'єднання з базою даних                  |

🔒 — потребує заголовка `Authorization: Bearer <access_token>`.

Пошук — `first_name`, `last_name`, `email` (частковий збіг без урахування регістру,
поєднуються через `AND`) плюс `skip`/`limit`. Дні народження порівнюються лише за
місяцем і днем, тому вікно працює через межу року (28.12 → 03.01).

Коди відповідей: некоректні дані → `422`, дублікат → `409`, неіснуючий або чужий
контакт → `404`, невалідний токен → `401`, бракує прав → `403`.

### Ролі

Роль задається під час реєстрації (`"role": "admin"`) або змінюється в базі.
Звичайний користувач із роллю `user` лишається з аватаром за замовчуванням
(Gravatar) — спроба змінити його повертає `403`.

### Скидання пароля

1. `POST /api/auth/password_reset_request` з email. Відповідь однакова незалежно
   від того, чи існує такий користувач, щоб маршрут не перетворився на перевірку
   зареєстрованих адрес.
2. На пошту надходить одноразовий JWT (типово діє годину).
3. `POST /api/auth/reset_password` з `token` і `new_password` встановлює новий
   пароль і скидає кеш користувача.

## Тести

```bash
poetry run pytest                              # усі тести
poetry run pytest --cov --cov-report=term-missing   # зі звітом про покриття
poetry run pytest --cov --cov-report=html      # HTML-звіт у htmlcov/
```

```
tests/
├── conftest.py                        # тестова база, клієнт, токени
├── test_unit_repository_contacts.py   # модульні тести репозиторіїв
├── test_unit_repository_users.py
├── test_unit_services_auth.py         # паролі, токени, ролі, кеш
├── test_unit_services_cache.py        # Redis-кеш на підробленому клієнті
├── test_unit_services_contacts.py
├── test_unit_services_email.py
├── test_unit_services_upload_file.py
├── test_unit_database_db.py
├── test_unit_main.py
├── test_integration_auth.py           # інтеграційні тести маршрутів
├── test_integration_contacts.py
├── test_integration_users.py
└── test_integration_utils.py
```

## Документація (Sphinx)

```bash
cd docs
poetry run make html        # результат — docs/_build/html/index.html
```

Документація збирається з docstrings безпосередньо в коді (`sphinx.ext.autodoc`)

## Структура

Усі налаштування — у `.env` (шаблон у `.env.example`), у коді секретів немає

```
main.py               # точка входу, CORS, rate limiting, роутери
Dockerfile            # образ застосунку
docker-compose.yml    # PostgreSQL + Redis + API
migrations/           # міграції Alembic
docs/                 # джерела документації Sphinx
tests/                # модульні та інтеграційні тести
src/
├── api/              # роути (auth, users, contacts, healthchecker)
├── conf/config.py    # налаштування з .env
├── database/         # менеджер async-сесій та ORM-моделі
├── repository/       # шар доступу до даних (contacts, users)
├── services/         # бізнес-логіка, JWT, кеш, email, Cloudinary, rate limiter
└── schemas.py        # Pydantic-схеми
```

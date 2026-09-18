"""Маршрути аутентифікації: реєстрація, вхід, оновлення токенів,
підтвердження пошти та скидання пароля.
"""

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.schemas import (
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    RequestEmail,
    Token,
    User,
    UserCreate,
)
from src.services.auth import (
    Hash,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_email_from_reset_token,
    get_email_from_token,
)
from src.services.email import send_email, send_reset_password_email
from src.services.users import UserService

router = APIRouter(prefix="/auth", tags=["auth"])

#: Однакова відповідь на будь-який запит скидання пароля, щоб не дати змоги
#: дізнатися, які адреси зареєстровані в системі.
RESET_REQUEST_MESSAGE = (
    "Якщо така електронна адреса зареєстрована, ми надіслали лист "
    "з інструкціями для скидання пароля"
)


async def _issue_tokens(username: str) -> Token:
    """Створює пару ``access_token`` / ``refresh_token`` для користувача.

    :param username: ім'я користувача, що потрапляє в claim ``sub``.
    :type username: str
    :return: пара токенів.
    :rtype: Token
    """
    return Token(
        access_token=await create_access_token(data={"sub": username}),
        refresh_token=await create_refresh_token(data={"sub": username}),
        token_type="bearer",
    )


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Реєструє користувача й надсилає лист із підтвердженням пошти.

    :param user_data: дані реєстрації.
    :type user_data: UserCreate
    :param background_tasks: черга фонових задач FastAPI.
    :type background_tasks: BackgroundTasks
    :param request: HTTP-запит (потрібен для базового URL у листі).
    :type request: Request
    :param db: сесія бази даних.
    :type db: AsyncSession
    :raises HTTPException: 409, якщо email або ім'я користувача вже зайняті.
    :return: створений користувач.
    :rtype: User
    """
    user_service = UserService(db)

    if await user_service.get_user_by_email(str(user_data.email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач з таким email вже існує",
        )
    if await user_service.get_user_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач з таким іменем вже існує",
        )

    hashed_password = Hash().get_password_hash(user_data.password)
    new_user = await user_service.create_user(user_data, hashed_password)
    background_tasks.add_task(
        send_email, new_user.email, new_user.username, str(request.base_url)
    )
    return new_user


@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Автентифікує користувача та повертає пару JWT-токенів.

    :param form_data: форма OAuth2 з полями ``username`` і ``password``.
    :type form_data: OAuth2PasswordRequestForm
    :param db: сесія бази даних.
    :type db: AsyncSession
    :raises HTTPException: 401, якщо облікові дані хибні або пошта
        не підтверджена.
    :return: ``access_token`` і ``refresh_token``.
    :rtype: Token
    """
    user = await UserService(db).get_user_by_username(form_data.username)
    if not user or not Hash().verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неправильний логін або пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Електронна адреса не підтверджена",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await _issue_tokens(user.username)


@router.post("/refresh_token", response_model=Token)
async def refresh_tokens(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Видає нову пару токенів в обмін на дійсний ``refresh_token``.

    Токен доступу навмисно короткоживучий, тому клієнт продовжує сесію
    саме через цей маршрут, не надсилаючи пароль повторно.

    :param body: тіло запиту з refresh-токеном.
    :type body: RefreshTokenRequest
    :param db: сесія бази даних.
    :type db: AsyncSession
    :raises HTTPException: 401, якщо токен недійсний або користувача немає.
    :return: нова пара токенів.
    :rtype: Token
    """
    username = await decode_refresh_token(body.refresh_token)
    user = await UserService(db).get_user_by_username(username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недійсний refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await _issue_tokens(user.username)


@router.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db: AsyncSession = Depends(get_db)):
    """Підтверджує електронну пошту за токеном із листа.

    :param token: токен підтвердження.
    :type token: str
    :param db: сесія бази даних.
    :type db: AsyncSession
    :raises HTTPException: 400, якщо користувача з такою адресою немає.
    :return: повідомлення про результат.
    :rtype: dict
    """
    email = await get_email_from_token(token)
    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if user.confirmed:
        return {"message": "Ваша електронна пошта вже підтверджена"}
    await user_service.confirmed_email(email)
    return {"message": "Електронну пошту підтверджено"}


@router.post("/request_email")
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Повторно надсилає лист із підтвердженням електронної пошти.

    :param body: тіло запиту з адресою.
    :type body: RequestEmail
    :param background_tasks: черга фонових задач FastAPI.
    :type background_tasks: BackgroundTasks
    :param request: HTTP-запит (потрібен для базового URL у листі).
    :type request: Request
    :param db: сесія бази даних.
    :type db: AsyncSession
    :return: повідомлення про результат.
    :rtype: dict
    """
    user = await UserService(db).get_user_by_email(str(body.email))
    if user and user.confirmed:
        return {"message": "Ваша електронна пошта вже підтверджена"}
    if user:
        background_tasks.add_task(
            send_email, user.email, user.username, str(request.base_url)
        )
    return {"message": "Перевірте свою електронну пошту для підтвердження"}


@router.post("/password_reset_request")
async def password_reset_request(
    body: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Надсилає лист із посиланням для скидання пароля.

    Відповідь однакова незалежно від того, чи існує такий користувач, —
    інакше маршрут перетворився б на перевірку зареєстрованих адрес.

    :param body: тіло запиту з електронною адресою.
    :type body: PasswordResetRequest
    :param background_tasks: черга фонових задач FastAPI.
    :type background_tasks: BackgroundTasks
    :param request: HTTP-запит (потрібен для базового URL у листі).
    :type request: Request
    :param db: сесія бази даних.
    :type db: AsyncSession
    :return: нейтральне повідомлення про надсилання листа.
    :rtype: dict
    """
    user = await UserService(db).get_user_by_email(str(body.email))
    if user:
        background_tasks.add_task(
            send_reset_password_email,
            user.email,
            user.username,
            str(request.base_url),
        )
    return {"message": RESET_REQUEST_MESSAGE}


@router.get("/reset_password/{token}")
async def verify_reset_token(token: str):
    """Перевіряє токен зі скидання пароля (посилання з листа).

    :param token: токен скидання пароля.
    :type token: str
    :raises HTTPException: 422, якщо токен недійсний або прострочений.
    :return: адреса, для якої дійсний токен, і підказка щодо наступного кроку.
    :rtype: dict
    """
    email = await get_email_from_reset_token(token)
    return {
        "email": email,
        "message": (
            "Токен дійсний. Надішліть POST-запит на /api/auth/reset_password "
            "з цим токеном і новим паролем"
        ),
    }


@router.post("/reset_password")
async def reset_password(
    body: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Встановлює новий пароль за токеном зі скидання.

    :param body: токен із листа та новий пароль.
    :type body: PasswordResetConfirm
    :param db: сесія бази даних.
    :type db: AsyncSession
    :raises HTTPException: 422, якщо токен недійсний; 404, якщо користувача
        з такою адресою вже не існує.
    :return: повідомлення про успішну зміну пароля.
    :rtype: dict
    """
    email = await get_email_from_reset_token(body.token)
    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Користувача не знайдено"
        )
    hashed_password = Hash().get_password_hash(body.new_password)
    await user_service.update_password(email, hashed_password)
    return {"message": "Пароль успішно змінено"}

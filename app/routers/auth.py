# app/routers/auth.py
from app import routers
from datetime import timedelta
from app.core.config import settings
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import get_db
from app.db.models import User
from app.schemas.user import UserCreate, UserResponse
from app.core.security import get_password_hash
from app.dependencies import get_current_user
from app.core.security import verify_password, create_access_token
from app.schemas.token import Token, LoginRequest
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Проверяем есть ли такой номер в базе
    query = select(User).where(User.phone == user_data.phone)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким номером уже существует"
        )

    # Хешируем пароль
    hashed_password = get_password_hash(user_data.password)

    # Создаем пользователя
    new_user = User(
        phone=user_data.phone,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        role="user"
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):

    query = select(User).where(User.phone == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный номер телефона или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.phone},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
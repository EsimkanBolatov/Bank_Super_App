from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.db.database import get_db
from app.db.models import User

# Указываем FastAPI, где брать токен (из эндпоинта /auth/login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невалидный токен или истек срок действия",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 1. Декодируем токен
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        phone: str = payload.get("sub")  # Достаем номер телефона (мы его туда положили при логине)

        if phone is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # 2. Ищем пользователя в базе
    query = select(User).where(User.phone == phone)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user
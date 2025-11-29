from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/settings", tags=["Settings"])


# Схема ответа (данные профиля)
class UserProfile(BaseModel):
    phone: str
    full_name: str | None
    avatar_url: str | None
    role: str

    class Config:
        from_attributes = True


# Схема запроса на обновление
class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None


@router.get("/me", response_model=UserProfile)
async def get_profile_settings(current_user: User = Depends(get_current_user)):
    """Получить данные профиля для экрана настроек"""
    return current_user


@router.patch("/me", response_model=UserProfile)
async def update_profile_settings(
        req: UpdateProfileRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Обновить фото или имя в настройках"""
    if req.full_name is not None:
        current_user.full_name = req.full_name
    if req.avatar_url is not None:
        current_user.avatar_url = req.avatar_url

    await db.commit()
    await db.refresh(current_user)
    return current_user
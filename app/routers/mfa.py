import random
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db.models import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/mfa", tags=["MFA (Security)"])

# Временное хранилище кодов: { "номер_телефона": "1234" }
# В реальном проде используют Redis
otp_storage = {}


class OTPVerify(BaseModel):
    code: str


@router.post("/generate")
async def generate_otp(current_user: User = Depends(get_current_user)):
    # Генерируем код
    code = str(random.randint(1000, 9999))

    #  Сохраняем в память (перезаписываем старый, если был)
    otp_storage[current_user.phone] = code

    # 3. Эмуляция отправки СМС
    print(f"\n========== SMS SERVICE ==========")
    print(f"To: {current_user.phone}")
    print(f"Code: {code}")
    print(f"=================================\n")

    return {"message": "Код отправлен по SMS (смотрите консоль сервера)"}


@router.post("/verify")
async def verify_otp(
        otp_data: OTPVerify,
        current_user: User = Depends(get_current_user)
):
    # Получаем сохраненный код для этого юзера
    saved_code = otp_storage.get(current_user.phone)

    # Если кода нет или он не совпадает
    if not saved_code:
        raise HTTPException(status_code=400, detail="Код не был запрошен или истек")

    if saved_code != otp_data.code:
        raise HTTPException(status_code=400, detail="Неверный код")

    # Если всё ок — удаляем код (чтобы нельзя было использовать дважды)
    del otp_storage[current_user.phone]

    return {"status": "success", "message": "MFA пройден успешно"}
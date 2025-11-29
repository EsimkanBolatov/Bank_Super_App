import random
import urllib.request
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db.models import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/mfa", tags=["MFA (Security)"])

# Временное хранилище кодов (в проде используют Redis)
otp_storage = {}


class OTPVerify(BaseModel):
    code: str


# --- НАСТРОЙКИ TELEGRAM (Опционально) ---
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""


def send_telegram_message(text: str):
    """Отправляет сообщение в Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            print(f"Telegram status: {response.getcode()}")
    except Exception as e:
        print(f"Telegram Error: {e}")


@router.post("/generate")
async def generate_otp(current_user: User = Depends(get_current_user)):
    # 1. Генерируем код
    code = str(random.randint(1000, 9999))

    # 2. Сохраняем в память
    otp_storage[current_user.phone] = code

    # 3. Логирование в консоль (для истории)
    print(f"\n========== SMS SERVICE ==========")
    print(f"To: {current_user.phone}")
    print(f"Code: {code}")
    print(f"=================================\n")

    # 4. Отправка в Telegram (если настроен)
    if TELEGRAM_BOT_TOKEN:
        send_telegram_message(f"BellyBank Code: {code}")

    # 5. ВОЗВРАЩАЕМ КОД ВО ФРОНТЕНД (Эмуляция Push)
    return {
        "message": "Код отправлен",
        "demo_code": code  # <--- Фронтенд увидит это поле
    }


@router.post("/verify")
async def verify_otp(
        otp_data: OTPVerify,
        current_user: User = Depends(get_current_user)
):
    # Получаем сохраненный код
    saved_code = otp_storage.get(current_user.phone)

    if not saved_code:
        raise HTTPException(status_code=400, detail="Код не был запрошен или истек")

    if saved_code != otp_data.code:
        raise HTTPException(status_code=400, detail="Неверный код")

    # Удаляем код после успеха
    del otp_storage[current_user.phone]

    return {"status": "success", "message": "MFA пройден успешно"}
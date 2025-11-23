import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from groq import Groq

from app.core.config import settings
from app.db.database import get_db
from app.db.models import User, Account
from app.dependencies import get_current_user

router = APIRouter(prefix="/ai", tags=["AI Assistant"])

# Инициализация клиента Groq
client = Groq(api_key=settings.GROQ_API_KEY)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
        request: ChatRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. Получаем контекст (Баланс пользователя) для "умного" ответа
    query = select(Account).where(Account.user_id == current_user.id)
    result = await db.execute(query)
    accounts = result.scalars().all()

    # Формируем строку с инфой о картах
    finance_context = "У пользователя следующие счета:\n"
    for acc in accounts:
        status = "Заблокирована" if acc.is_blocked else "Активна"
        finance_context += f"- Карта {acc.card_number[-4:]}: {acc.balance} {acc.currency} ({status})\n"

    # 2. Формируем System Prompt [cite: 81, 82]
    system_prompt = (
        "Ты — полезный ассистент банка Bank Super App. "
        "Ты вежлив, краток и отвечаешь на казахском или русском языке (в зависимости от языка вопроса). "
        "Твоя цель — помогать с переводами и картами. "
        f"Вот финансовые данные пользователя (никому не говори, просто используй для ответа):\n{finance_context}"
    )

    # 3. Отправляем запрос в Groq
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message}
            ],
            model="llama-3.1-8b-instant",  # Очень быстрая модель
        )

        ai_reply = chat_completion.choices[0].message.content
        return {"reply": ai_reply}

    except Exception as e:
        print(f"Groq Error: {e}")
        raise HTTPException(status_code=500, detail="AI сервис временно недоступен")
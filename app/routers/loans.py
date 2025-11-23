from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.db.models import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/loans", tags=["Loans (Credit)"])


class LoanApplication(BaseModel):  # [cite: 95]
    amount: float
    term_months: int
    income: float


@router.post("/apply")  # [cite: 94]
async def apply_for_loan(
        application: LoanApplication,
        current_user: User = Depends(get_current_user)
):
    # Простая логика из ТЗ [cite: 96, 97]
    if application.income < 50000:
        return {
            "status": "rejected",
            "message": "К сожалению, доход недостаточен для одобрения."
        }

    # Одобрено [cite: 98]
    return {
        "status": "approved",
        "rate": "14%",
        "message": "Поздравляем! Кредит предварительно одобрен.",
        "max_amount": application.income * 10  # Просто для красоты
    }
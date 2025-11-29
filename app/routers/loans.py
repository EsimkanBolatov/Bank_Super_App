from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from datetime import datetime, timedelta
from decimal import Decimal

from app.db.database import get_db
from app.db.models import User, Account, Transaction
from app.dependencies import get_current_user

router = APIRouter(prefix="/loans", tags=["Loans"])


class LoanRequest(BaseModel):
    amount: float
    term_months: int
    income: float


@router.post("/apply")
async def apply_loan(
        req: LoanRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Скоринг
    rate = 0.15
    m_rate = rate / 12
    if m_rate > 0:
        payment = req.amount * (m_rate / (1 - (1 + m_rate) ** -req.term_months))
    else:
        payment = req.amount / req.term_months

    if payment > (req.income * 0.5):  # Увеличил лимит до 50%
        return {"status": "rejected", "message": "Высокая кредитная нагрузка"}

    # Поиск счета
    q = select(Account).where(Account.user_id == current_user.id)
    res = await db.execute(q)
    acc = res.scalars().first()

    if not acc:
        raise HTTPException(status_code=400, detail="Счет не найден")

    try:
        amount_dec = Decimal(str(req.amount))
        acc.balance += amount_dec  # Зачисляем деньги

        tx = Transaction(
            from_account_id=None,  # Из банка
            to_account_id=acc.id,
            amount=amount_dec,
            category="Loan Disbursement",
            created_at=datetime.utcnow()
        )
        db.add(tx)
        await db.commit()
        await db.refresh(tx)

        # График
        schedule = []
        curr = datetime.now()
        bal = req.amount
        for i in range(1, req.term_months + 1):
            date = curr + timedelta(days=30 * i)
            interest = bal * m_rate
            principal = payment - interest
            bal -= principal
            schedule.append({
                "date": date.strftime("%d.%m.%Y"),
                "amount": round(payment, 2)
            })

        return {"status": "approved", "rate": "15%", "schedule": schedule}

    except Exception as e:
        await db.rollback()
        print(f"Loan Error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка оформления кредита")
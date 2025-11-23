from decimal import Decimal  # <--- 1. ВАЖНО: Импорт
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
from app.db.models import User, Account, Transaction
from app.dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/services", tags=["Services"])


class ServicePayment(BaseModel):
    service_name: str
    amount: float


@router.post("/pay")
async def pay_service(
        payment: ServicePayment,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    query = select(Account).where(Account.user_id == current_user.id)
    result = await db.execute(query)
    account = result.scalars().first()

    if not account:
        raise HTTPException(status_code=400, detail="Нет счета для оплаты")

    amount_decimal = Decimal(str(payment.amount))

    if account.balance < amount_decimal:
        raise HTTPException(status_code=400, detail="Недостаточно средств")

    account.balance -= amount_decimal

    new_tx = Transaction(
        from_account_id=account.id,
        to_account_id=account.id,
        amount=amount_decimal,
        category=payment.service_name
    )

    db.add(new_tx)
    await db.commit()

    return {"status": "success", "message": f"Оплата {payment.service_name} прошла успешно"}
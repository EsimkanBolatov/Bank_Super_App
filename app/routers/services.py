from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

from app.db.database import get_db
from app.db.models import User, Account, Transaction, RoleEnum, CurrencyEnum
from app.dependencies import get_current_user

router = APIRouter(prefix="/services", tags=["Services"])


class PayServiceRequest(BaseModel):
    service_name: str
    amount: float


# Настройка: Куда уходят деньги
SERVICE_ACCOUNTS_MAP = {
    "ITU Tuition": {"phone": "service_itu", "name": "ITU University", "card": "ITU_CORP_ACC"},
    "Eco Tree": {"phone": "service_eco", "name": "Eco Fund KZ", "card": "ECO_FUND_ACC"},
    "Digital Taraz": {"phone": "service_bus", "name": "Tulpar Transport", "card": "BUS_PARK_ACC"},
    "Taksi": {"phone": "service_taxi", "name": "Taxi Aggregator", "card": "TAXI_CORP_ACC"},
}


async def get_or_create_service_account(db: AsyncSession, service_name: str) -> Account:
    """Находит или создает счет компании-получателя."""
    info = SERVICE_ACCOUNTS_MAP.get(service_name,
                                    {"phone": "service_misc", "name": "General Service", "card": "MISC_ACC"})

    # 1. Ищем юзера-компанию
    q = select(User).where(User.phone == info["phone"])
    res = await db.execute(q)
    user = res.scalars().first()

    if not user:
        user = User(phone=info["phone"], password_hash="service_pass", full_name=info["name"], role=RoleEnum.USER)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # 2. Ищем счет компании
    q_acc = select(Account).where(Account.user_id == user.id)
    res_acc = await db.execute(q_acc)
    acc = res_acc.scalars().first()

    if not acc:
        acc = Account(user_id=user.id, card_number=info["card"], balance=0, currency=CurrencyEnum.KZT)
        db.add(acc)
        await db.commit()
        await db.refresh(acc)

    return acc


@router.post("/pay")
async def pay_service(
        req: PayServiceRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. Счет плательщика
    q = select(Account).where(Account.user_id == current_user.id, Account.is_blocked == False)
    res = await db.execute(q)
    user_acc = res.scalars().first()

    if not user_acc:
        raise HTTPException(status_code=400, detail="Нет счета для оплаты")

    amount = Decimal(str(req.amount))
    if user_acc.balance < amount:
        raise HTTPException(status_code=400, detail="Недостаточно средств")

    # 2. Счет получателя (Сервиса)
    service_acc = await get_or_create_service_account(db, req.service_name)

    try:
        # Перевод
        user_acc.balance -= amount
        service_acc.balance += amount

        # История
        tx = Transaction(
            from_account_id=user_acc.id,
            to_account_id=service_acc.id,  # ID счета сервиса!
            amount=amount,
            category=f"Service: {req.service_name}",
            created_at=datetime.utcnow()
        )
        db.add(tx)
        await db.commit()
        await db.refresh(tx)

        return {"status": "success", "message": f"Оплачено: {req.service_name}", "new_balance": float(user_acc.balance)}

    except Exception as e:
        await db.rollback()
        print(f"Service Error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка проведения платежа")
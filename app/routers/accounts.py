import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
from app.db.models import Account, User, CurrencyEnum
from app.dependencies import get_current_user
from pydantic import BaseModel

from decimal import Decimal
from app.db.models import Transaction
from datetime import datetime

router = APIRouter(prefix="/accounts", tags=["Accounts"])


# Схема для создания счета (принимаем только валюту)
class AccountCreate(BaseModel):
    currency: CurrencyEnum = CurrencyEnum.KZT


# Схема для ответа (показываем баланс и номер карты)
class AccountResponse(BaseModel):
    id: int
    card_number: str
    balance: float
    currency: str
    is_blocked: bool

    class Config:
        from_attributes = True

class DepositRequest(BaseModel):
    card_number: str
    amount: float

def generate_card_number():
    """Генерирует случайный 16-значный номер, начинающийся с 4 (Visa)"""
    # нужен алгоритм Луна.
    prefix = "4000"
    suffix = "".join([str(random.randint(0, 9)) for _ in range(12)])
    return prefix + suffix

@router.post("/create", response_model=AccountResponse)
async def create_account(
        account_data: AccountCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Генерируем уникальный номер карты
    # (в идеале надо проверять в цикле, нет ли такой карты в БД, но для MVP пропустим)
    card_number = generate_card_number()

    # Создаем счет
    new_account = Account(
        user_id=current_user.id,  # Привязываем к тому, кто залогинен
        card_number=card_number,
        balance=0.00,
        currency=account_data.currency,
        is_blocked=False
    )

    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)

    return new_account


@router.get("/", response_model=list[AccountResponse])
async def get_my_accounts(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    query = select(Account).where(Account.user_id == current_user.id)
    result = await db.execute(query)
    accounts = result.scalars().all()
    return accounts


@router.patch("/{account_id}/block")  # [cite: 88]
async def block_account(
        account_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Ищем счет и проверяем, что он принадлежит текущему юзеру
    query = select(Account).where(Account.id == account_id, Account.user_id == current_user.id)
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Счет не найден")

    account.is_blocked = True  # [cite: 89]
    await db.commit()

    return {"status": "success", "message": "Карта заблокирована 🔒"}


@router.patch("/{account_id}/unblock")  # [cite: 90]
async def unblock_account(
        account_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    query = select(Account).where(Account.id == account_id, Account.user_id == current_user.id)
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Счет не найден")

    account.is_blocked = False
    await db.commit()

    return {"status": "success", "message": "Карта разблокирована ✅"}


@router.post("/deposit")
async def deposit_money(
        deposit: DepositRequest,
        db: AsyncSession = Depends(get_db),
        # current_user: User = Depends(get_current_user) # Можно убрать, если хотим, чтобы это был "Публичный банкомат"
):
    """
    Эмуляция пополнения через банкомат/терминал.
    Не требует авторизации (или можно оставить, если нужно).
    """
    # 1. Ищем карту по номеру
    query = select(Account).where(Account.card_number == deposit.card_number)
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Карта не найдена")

    if account.is_blocked:
        raise HTTPException(status_code=400, detail="Карта заблокирована, пополнение невозможно")

    # 2. Конвертируем сумму в Decimal (важно для денег!)
    amount_decimal = Decimal(str(deposit.amount))

    if amount_decimal <= 0:
        raise HTTPException(status_code=400, detail="Сумма должна быть больше 0")

    # 3. Зачисляем деньги
    account.balance += amount_decimal

    # 4. Создаем запись в истории (Транзакция)
    # from_account_id=None означает, что деньги пришли "извне" (банкомат)
    new_transaction = Transaction(
        from_account_id=None,
        to_account_id=account.id,
        amount=amount_decimal,
        category="ATM Deposit",  # Красивая категория для истории
        created_at=datetime.utcnow()
    )

    db.add(new_transaction)
    await db.commit()
    await db.refresh(account)

    return {
        "status": "success",
        "message": f"Зачислено {deposit.amount} {account.currency}",
        "new_balance": account.balance
    }
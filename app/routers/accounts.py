import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
from app.db.models import Account, User, CurrencyEnum
from app.dependencies import get_current_user
from pydantic import BaseModel

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
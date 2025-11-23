from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, desc

from app.db.database import get_db
from app.db.models import User, Transaction, Account
from app.dependencies import get_current_user
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/transactions", tags=["History"])


class TransactionSchema(BaseModel):
    id: int
    amount: float
    category: str
    created_at: datetime
    type: str

    class Config:
        from_attributes = True


@router.get("/", response_model=list[TransactionSchema])
async def get_history(
        limit: int = 20,
        offset: int = 0,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    query_accounts = select(Account.id).where(Account.user_id == current_user.id)
    result_accounts = await db.execute(query_accounts)
    user_account_ids = result_accounts.scalars().all()

    if not user_account_ids:
        return []

    query = select(Transaction).where(
        or_(
            Transaction.from_account_id.in_(user_account_ids),
            Transaction.to_account_id.in_(user_account_ids)
        )
    ).order_by(desc(Transaction.created_at)).limit(limit).offset(offset)

    result = await db.execute(query)
    transactions = result.scalars().all()

    history = []
    for tx in transactions:
        tx_type = "expense" if tx.from_account_id in user_account_ids else "income"
        history.append({
            "id": tx.id,
            "amount": tx.amount,
            "category": tx.category,
            "created_at": tx.created_at,
            "type": tx_type
        })

    return history
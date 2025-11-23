from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import User, Account, Transaction
from app.schemas.transfer import TransferRequest
from app.dependencies import get_current_user

router = APIRouter(prefix="/transfers", tags=["Transfers"])


@router.post("/p2p")
async def make_transfer(
        transfer: TransferRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. Находим счет ОТПРАВИТЕЛЯ (берем первый попавшийся счет в KZT)
    # В реальном приложении юзер выбирает, с какой карты платить
    query_sender = select(Account).where(
        Account.user_id == current_user.id,
        Account.is_blocked == False
    )
    result_sender = await db.execute(query_sender)
    sender_account = result_sender.scalars().first()

    if not sender_account:
        raise HTTPException(status_code=400, detail="У вас нет активного счета для списания")

    if sender_account.is_blocked:
        raise HTTPException(status_code=403, detail="Карта заблокирована. Перевод невозможен.")  

    if sender_account.balance < transfer.amount:
        raise HTTPException(status_code=400, detail="Недостаточно средств")

    # 2. Находим счет ПОЛУЧАТЕЛЯ
    recipient_account = None

    if transfer.to_card:
        # Ищем по карте
        query_recipient = select(Account).where(Account.card_number == transfer.to_card)
        res = await db.execute(query_recipient)
        recipient_account = res.scalar_one_or_none()

    elif transfer.to_phone:
        # Ищем юзера по телефону, потом его счет
        query_user = select(User).where(User.phone == transfer.to_phone).options(selectinload(User.accounts))
        res = await db.execute(query_user)
        recipient_user = res.scalar_one_or_none()

        if recipient_user and recipient_user.accounts:
            recipient_account = recipient_user.accounts[0]  # Шлем на первую карту

    if not recipient_account:
        raise HTTPException(status_code=404, detail="Получатель не найден")

    if sender_account.id == recipient_account.id:
        raise HTTPException(status_code=400, detail="Нельзя переводить самому себе на ту же карту")

    # 3. ТРАНЗАКЦИЯ (ACID)
    try:
        # Списание
        sender_account.balance -= transfer.amount
        # Зачисление
        recipient_account.balance += transfer.amount

        # Запись в историю
        new_transaction = Transaction(
            from_account_id=sender_account.id,
            to_account_id=recipient_account.id,
            amount=transfer.amount,
            category="Transfer"
        )
        db.add(new_transaction)

        await db.commit()  # Сохраняем изменения

        return {"status": "success", "message": "Перевод выполнен", "transaction_id": new_transaction.id}

    except Exception as e:
        await db.rollback()  # Если что-то пошло не так — отменяем всё!
        raise HTTPException(status_code=500, detail="Ошибка при переводе")
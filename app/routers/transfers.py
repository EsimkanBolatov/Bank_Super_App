from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User, Account, Transaction, Favorite
from app.schemas.transfer import TransferRequest
from app.dependencies import get_current_user

router = APIRouter(prefix="/transfers", tags=["Transfers & Favorites"])

# --- СХЕМЫ ---
class FavoriteCreate(BaseModel):
    name: str
    value: str
    type: str

# --- ИЗБРАННОЕ ---
@router.get("/favorites")
async def get_favorites(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Пробуем получить избранное. Если таблицы нет - вернем пустой список, чтобы не крашить фронт.
    try:
        res = await db.execute(select(Favorite).where(Favorite.user_id == current_user.id))
        return [{"id": f.id, "name": f.name, "value": f.value, "type": f.type, "color": [f.color_start, f.color_end]} for f in res.scalars().all()]
    except Exception as e:
        print(f"Favorites DB Error (table missing?): {e}")
        return []

@router.post("/favorites")
async def add_favorite(fav: FavoriteCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_fav = Favorite(user_id=current_user.id, name=fav.name, value=fav.value, type=fav.type)
    db.add(new_fav)
    await db.commit()
    return {"status": "ok", "id": new_fav.id}

@router.delete("/favorites/{fav_id}")
async def delete_favorite(fav_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    res = await db.execute(select(Favorite).where(Favorite.id == fav_id, Favorite.user_id == current_user.id))
    if fav := res.scalar_one_or_none():
        await db.delete(fav)
        await db.commit()
    return {"status": "ok"}

# --- ПЕРЕВОДЫ ---
@router.post("/p2p")
async def make_transfer(
        transfer: TransferRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. ОТПРАВИТЕЛЬ (С какой карты?)
    sender_account = None
    if transfer.from_account_id:
        # Если фронт прислал ID карты — берем конкретную
        res = await db.execute(select(Account).where(Account.id == transfer.from_account_id, Account.user_id == current_user.id))
        sender_account = res.scalar_one_or_none()
    
    if not sender_account:
        # Иначе берем первую незаблокированную (Fallback)
        res = await db.execute(select(Account).where(Account.user_id == current_user.id, Account.is_blocked == False))
        sender_account = res.scalars().first()

    if not sender_account:
        raise HTTPException(status_code=400, detail="Нет доступных карт для списания")
    
    if sender_account.is_blocked:
        raise HTTPException(status_code=403, detail="Ваша карта заблокирована")

    if sender_account.balance < transfer.amount:
        raise HTTPException(status_code=400, detail=f"Недостаточно средств. Баланс: {sender_account.balance}")

    # 2. ПОЛУЧАТЕЛЬ
    recipient_account = None
    
    # Чистим входные данные
    clean_phone = transfer.to_phone.replace(" ", "").replace("(", "").replace(")", "").replace("-", "").replace("+", "") if transfer.to_phone else None
    # Превращаем 8777... или 7777... в 8777... для поиска в БД
    if clean_phone:
        if clean_phone.startswith("7") and len(clean_phone) == 11: clean_phone = "8" + clean_phone[1:]
        if len(clean_phone) == 10: clean_phone = "8" + clean_phone

    clean_card = transfer.to_card.replace(" ", "") if transfer.to_card else None

    # Логика поиска
    if clean_phone:
        # Ищем юзера
        res = await db.execute(select(User).where(User.phone == clean_phone).options(selectinload(User.accounts)))
        recipient_user = res.scalar_one_or_none()
        
        if not recipient_user:
            raise HTTPException(status_code=404, detail="Клиент с таким номером не найден в Belly Bank")
            
        if recipient_user.accounts:
            recipient_account = recipient_user.accounts[0] # Берем первую карту получателя
        else:
            raise HTTPException(status_code=400, detail="У получателя нет активных карт")

    elif clean_card:
        # Ищем по карте (внутри банка)
        res = await db.execute(select(Account).where(Account.card_number == clean_card))
        recipient_account = res.scalar_one_or_none()

    # 3. ПРОВЕРКИ
    if recipient_account and sender_account.id == recipient_account.id:
        raise HTTPException(status_code=400, detail="Выбрана одна и та же карта. Выберите другую карту для зачисления.")

    # 4. ПРОВЕДЕНИЕ ПЛАТЕЖА
    try:
        sender_account.balance -= transfer.amount
        
        if recipient_account:
            # Внутренний перевод
            recipient_account.balance += transfer.amount
            desc = "Перевод клиенту банка"
            to_id = recipient_account.id
        else:
            # Внешний перевод (если номер карты не наш)
            # В реальности тут запрос к Visa/Mastercard
            desc = f"Перевод на другую карту (*{clean_card[-4:] if clean_card else 'EXT'})"
            to_id = None

        tx = Transaction(
            from_account_id=sender_account.id,
            to_account_id=to_id,
            amount=transfer.amount,
            category=desc
        )
        db.add(tx)
        await db.commit()
        
        return {"status": "success", "message": "Перевод успешно выполнен"}

    except Exception as e:
        await db.rollback()
        print(f"Transfer error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера при переводе")
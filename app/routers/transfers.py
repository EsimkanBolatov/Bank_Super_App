from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User, Account, Transaction, Favorite
from app.schemas.transfer import TransferRequest
from app.dependencies import get_current_user

router = APIRouter(prefix="/transfers", tags=["Transfers & Favorites"])

# --- СХЕМЫ ДЛЯ ИЗБРАННОГО ---
class FavoriteCreate(BaseModel):
    name: str
    value: str
    type: str # phone / card

class FavoriteResponse(BaseModel):
    id: int
    name: str
    value: str
    type: str
    color: list[str] # Вернем как массив для фронта

# --- ЛОГИКА ПЕРЕВОДОВ ---

@router.post("/p2p")
async def make_transfer(
        transfer: TransferRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. Ищем отправителя (ОБЯЗАТЕЛЬНО по ID, если он передан)
    sender_account = None
    if transfer.from_account_id:
        res = await db.execute(select(Account).where(Account.id == transfer.from_account_id, Account.user_id == current_user.id))
        sender_account = res.scalar_one_or_none()
    
    # Если ID не передан или карта не найдена — берем дефолтную
    if not sender_account:
        res = await db.execute(select(Account).where(Account.user_id == current_user.id, Account.is_blocked == False))
        sender_account = res.scalars().first()

    if not sender_account:
        raise HTTPException(status_code=400, detail="Нет счетов для списания")
    
    if sender_account.balance < transfer.amount:
        raise HTTPException(status_code=400, detail="Недостаточно средств")

    # 2. Ищем получателя
    recipient_account = None

    # Очистка данных
    clean_card = transfer.to_card.replace(" ", "") if transfer.to_card else None
    clean_phone = transfer.to_phone.replace(" ", "").replace("(", "").replace(")", "").replace("-", "").replace("+", "") if transfer.to_phone else None
    if clean_phone and clean_phone.startswith("7"): clean_phone = "8" + clean_phone[1:]

    # Поиск
    if clean_card:
        res = await db.execute(select(Account).where(Account.card_number == clean_card))
        recipient_account = res.scalar_one_or_none()
    elif clean_phone:
        res = await db.execute(select(User).where(User.phone == clean_phone).options(selectinload(User.accounts)))
        recipient_user = res.scalar_one_or_none()
        if recipient_user and recipient_user.accounts:
            recipient_account = recipient_user.accounts[0]

    # ПРОВЕРКА НА САМОГО СЕБЯ
    if recipient_account and sender_account.id == recipient_account.id:
        raise HTTPException(status_code=400, detail="Нельзя перевести на ту же карту. Выберите другую карту зачисления.")

    # 3. ТРАНЗАКЦИЯ
    try:
        sender_account.balance -= transfer.amount
        
        if recipient_account:
            recipient_account.balance += transfer.amount
            desc = "Перевод клиенту банка"
            to_id = recipient_account.id
        else:
            # Внешний перевод (эмуляция)
            desc = f"Вывод на карту другого банка ({clean_card[-4:] if clean_card else 'External'})"
            to_id = None

        new_tx = Transaction(
            from_account_id=sender_account.id,
            to_account_id=to_id,
            amount=transfer.amount,
            category=desc
        )
        db.add(new_tx)
        await db.commit()
        return {"status": "success", "message": "Перевод отправлен"}

    except Exception as e:
        await db.rollback()
        print(f"Transfer Error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера при переводе")

# --- ЛОГИКА ИЗБРАННОГО ---

@router.get("/favorites")
async def get_favorites(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    res = await db.execute(select(Favorite).where(Favorite.user_id == current_user.id))
    favs = res.scalars().all()
    return [{"id": f.id, "name": f.name, "value": f.value, "type": f.type, "color": [f.color_start, f.color_end]} for f in favs]

@router.post("/favorites")
async def add_favorite(
    fav: FavoriteCreate,
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Простые цвета-заглушки
    new_fav = Favorite(
        user_id=current_user.id,
        name=fav.name,
        value=fav.value,
        type=fav.type,
        color_start="#FF9800", # Можно рандомизировать
        color_end="#F57C00"
    )
    db.add(new_fav)
    await db.commit()
    return {"status": "created", "id": new_fav.id}

@router.delete("/favorites/{fav_id}")
async def delete_favorite(fav_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    res = await db.execute(select(Favorite).where(Favorite.id == fav_id, Favorite.user_id == current_user.id))
    fav = res.scalar_one_or_none()
    if fav:
        await db.delete(fav)
        await db.commit()
    return {"status": "deleted"}
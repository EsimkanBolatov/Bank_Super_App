import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DECIMAL, DateTime, Enum
from sqlalchemy.orm import relationship
from app.db.database import Base

class CurrencyEnum(str, enum.Enum):
    KZT = "KZT"
    USD = "USD"
    EUR = "EUR"

class RoleEnum(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)  # Логин (телефон)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(Enum(RoleEnum), default=RoleEnum.USER)

    # Связь: Один юзер может иметь много счетов
    accounts = relationship("Account", back_populates="user")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    card_number = Column(String(16), unique=True, index=True, nullable=False)  # Номер карты
    balance = Column(DECIMAL(10, 2), default=0.00)  # Деньги храним в DECIMAL!
    currency = Column(Enum(CurrencyEnum), default=CurrencyEnum.KZT)
    is_blocked = Column(Boolean, default=False)

    user = relationship("User", back_populates="accounts")

    # Связи для транзакций (отправитель и получатель)
    outgoing_transactions = relationship("Transaction", foreign_keys="[Transaction.from_account_id]",
                                         back_populates="from_account")
    incoming_transactions = relationship("Transaction", foreign_keys="[Transaction.to_account_id]",
                                         back_populates="to_account")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    from_account_id = Column(Integer, ForeignKey("accounts.id"),
                             nullable=True)  # Может быть NULL при пополнении из банкомата
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    amount = Column(DECIMAL(10, 2), nullable=False)
    category = Column(String, default="Transfer")  # Taxi, Groceries, Transfer
    created_at = Column(DateTime, default=datetime.utcnow)

    from_account = relationship("Account", foreign_keys=[from_account_id], back_populates="outgoing_transactions")
    to_account = relationship("Account", foreign_keys=[to_account_id], back_populates="incoming_transactions")
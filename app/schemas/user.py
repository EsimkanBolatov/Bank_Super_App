from pydantic import BaseModel, constr

# Базовая схема (общие поля)
class UserBase(BaseModel):
    phone: str
    full_name: str | None = None

# Схема для РЕГИСТРАЦИИ (то, что шлет фронтенд)
class UserCreate(UserBase):
    password: str

# Схема для ОТВЕТА (то, что мы возвращаем фронтенду - без пароля!)
class UserResponse(UserBase):
    id: int
    role: str

    class Config:
        from_attributes = True # Чтобы Pydantic читал данные из SQLAlchemy моделей
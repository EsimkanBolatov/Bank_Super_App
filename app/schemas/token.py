from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

# Схема для входа (то, что шлет клиент)
class LoginRequest(BaseModel):
    phone: str
    password: str
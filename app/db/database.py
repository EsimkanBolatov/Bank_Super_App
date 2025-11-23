from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# движок (Engine)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True
)

# фабрику сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# базовый класс для моделей
class Base(DeclarativeBase):
    pass

# зависимость Dependency для получения сессии в эндпоинтах
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
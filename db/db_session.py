from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base


DATABASE_URL = "postgresql+asyncpg://clinic_bot:blop1234@localhost:5432/clinic_db"

engine = create_async_engine(DATABASE_URL, echo=True)

async_session_maker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


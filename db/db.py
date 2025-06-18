from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL



engine = create_async_engine(DATABASE_URL, echo=True)

async_session_maker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


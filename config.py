
import os
from dotenv import load_dotenv


load_dotenv()


BOT_TOKEN = os.getenv('BOT_TOKEN', 'тестовый_токен_по_умолчанию')
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://clinic_bot:blop1234@localhost:5432/clinic_db'
)

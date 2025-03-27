from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import asyncio

# Укажи данные своего PostgreSQL на Render
DATABASE_URL = "postgresql+asyncpg://username:password@host:port/dbname"  

async def check_tables():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = result.fetchall()
        if tables:
            print("Существующие таблицы:", [table[0] for table in tables])
        else:
            print("Нет таблиц в базе данных.")

asyncio.run(check_tables())

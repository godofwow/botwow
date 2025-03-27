import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, Update
from fastapi import FastAPI, Depends
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import uvicorn
from sqlalchemy import select
from models import User  # Убедитесь, что у вас есть модель User

# Загружаем переменные окружения
load_dotenv()

# Получаем токен, URL Webhook и URL базы данных из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

# Проверяем, что переменные окружения установлены
if not TOKEN or not WEBHOOK_URL or not DATABASE_URL:
    raise ValueError("Ошибка: BOT_TOKEN, WEBHOOK_URL или DATABASE_URL не найдены! Проверь .env файл или переменные окружения.")

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

# Создаем бота и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Инициализируем FastAPI
app = FastAPI()

# Настройка подключения к базе данных
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Обработчик команды /start
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Привет! Я твой Telegram-бот MaestroAI.")

# Обработчик текстовых сообщений
@dp.message()
async def echo_handler(message: Message):
    await message.answer(f"Ты сказал: {message.text}")

# Обработка Webhook
@app.post("/")
async def process_webhook(update: dict):
    telegram_update = Update(**update)
    await dp.feed_update(bot, telegram_update)
    return {"ok": True}

# Проверка статуса бота
@app.get("/")
async def health_check():
    return {"status": "Bot is running"}

from models import Base  # Убедись, что у тебя есть импорт Base (из models.py)

async def create_tables():
    async with engine.begin() as conn:
        logging.info("Создание таблиц...")
        try:
            await conn.run_sync(Base.metadata.create_all)
            logging.info("Таблицы успешно созданы или уже существуют.")
        except Exception as e:
            logging.error(f"Ошибка при создании таблиц: {e}")
        await conn.run_sync(Base.metadata.create_all)

# Устанавливаем Webhook при запуске
@app.on_event("startup")
async def on_startup():
    logging.info("Создание таблиц начинается...")  # Лог перед созданием
    await create_tables()  # Создаёт таблицы, если их нет
    logging.info("Создание таблиц завершено.")  # Лог после создания
    await bot.set_webhook(WEBHOOK_URL)
    # Отправляем сообщение пользователям
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User.telegram_id))
        chat_ids = [row[0] for row in result.fetchall()]
        for chat_id in chat_ids:
            try:
                await bot.send_message(chat_id, "Бот в работе")
            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Render выделяет порт в переменной окружения
    uvicorn.run(app, host="0.0.0.0", port=port)

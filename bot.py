import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, Update
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import uvicorn
from sqlalchemy import select
from models import User, Base  # Импорт моделей БД
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

from oauthlib.oauth2 import WebApplicationClient  # OAuth

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DATABASE_URL = os.getenv("DATABASE_URL")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Проверяем переменные окружения
if not all([TOKEN, WEBHOOK_URL, DATABASE_URL, MISTRAL_API_KEY]):
    raise ValueError("Ошибка: Убедитесь, что BOT_TOKEN, WEBHOOK_URL, DATABASE_URL и MISTRAL_API_KEY установлены.")

logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI()

client = MistralClient(api_key=MISTRAL_API_KEY)

def ask_gpt(prompt):
    messages = [ChatMessage(role="user", content=prompt)]
    
    response = client.chat(
        model="mistral-tiny",  # Можно заменить на "mistral-small" или "mistral-medium"
        messages=messages
    )

    return response.choices[0].message.content

# Настройка базы данных
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Обработчик команды /start
@dp.message(Command("start"))
async def start_handler(message: Message, db: AsyncSession = Depends(get_db)):
    user = await db.execute(select(User).where(User.telegram_id == message.from_user.id))
    if not user.scalar():
        db.add(User(telegram_id=message.from_user.id))
        await db.commit()
    await message.answer("Привет! Я твой Telegram-бот MaestroAI.")

# Обработка любых сообщений через GPT
@dp.message()
async def gpt_handler(message: Message):
    response = get_gpt_response(message.text)
    await message.answer(response)

# Обработка Webhook
@app.post("/")
async def process_webhook(update: dict):
    telegram_update = Update(**update)
    await dp.feed_update(bot, telegram_update)
    return {"ok": True}

# Проверка статуса
@app.get("/")
async def health_check():
    return {"status": "Bot is running"}

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("startup")
async def on_startup():
    await create_tables()
    await bot.set_webhook(WEBHOOK_URL)
    logging.info("Бот запущен")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

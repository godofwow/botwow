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
from mistralai import Mistral
from oauthlib.oauth2 import WebApplicationClient  # OAuth
from contextlib import asynccontextmanager

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

api_key = os.environ["MISTRAL_API_KEY"]
model = "mistral-large-latest"

client = Mistral(api_key=api_key)

chat_response = client.chat.complete(
    model= model,
    messages = [
        {
            "role": "user",
            "content": "What is the best French cheese?",
        },
    ]
)
print(chat_response.choices[0].message.content)

# Настройка базы данных
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Обработчик команды /start
@dp.message(Command("start"))
async def start_handler(message: Message):
    async with AsyncSessionLocal() as db:
        user = await db.execute(select(User).where(User.telegram_id == message.from_user.id))
        if not user.scalar():
            db.add(User(telegram_id=message.from_user.id))
            await db.commit()
    await message.answer("Привет! Я твой Telegram-бот MaestroAI.")
    
@dp.message()
async def mistral_handler(message: Message):
    try:
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[
                {"role": "user", "content": message.text},
            ]
        )
        await message.answer(response.choices[0].message.content)
    except Exception as e:
        logging.error(f"Ошибка при обработке запроса к Mistral: {e}")
        await message.answer("Произошла ошибка при обработке запроса. Попробуйте позже.")

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    await bot.set_webhook(WEBHOOK_URL)
    logging.info("Бот запущен")
    yield  # Позволяет корректно завершать приложение

app = FastAPI(lifespan=lifespan)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

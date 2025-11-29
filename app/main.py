import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy import select

from .config import settings
from .db import engine, async_session_maker
from .models import Base, User
from .weather_client import get_current_weather, format_weather_message

async def cmd_start(message: Message):
    async with async_session_maker() as session:
        user = await session.scalar(
            select(User).where(User.telegram_id == message.from_user.id)
        )

        if user is None:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
            )
            session.add(user)
        else:
            user.username = message.from_user.username

        await session.commit()

    await message.answer(
        "Привет! Я бот для уведомлений о погоде 🌤\n\n"
        "Пока я умею только здороваться, "
        "но скоро появятся команды:\n"
        "/set_city - выбрать город\n"
        "/subscribe_daily - подписаться на ежедневные уведомления\n"
        "/unsubscribe - отписаться\n"
        "/current - текущая погода"
    )

async def cmd_current(message: Message):
    async with async_session_maker() as session:
        user = await session.scalar(
            select(User).where(User.telegram_id == message.from_user.id)
        )
    if user is None:
        await message.answer("Я ещё не знаю, кто ты. Напиши сначала /start.")
        return

    if not user.city:
        await message.answer("Сначала задай город командой:\n/set_city <город>")
        return

    city = user.city

    try:
        data = await get_current_weather(city)
    except Exception as e:
        await message.answer(f"Не получилось получить погоду: {e}")
        return

    text = format_weather_message(city, data)
    await message.answer(text, parse_mode="HTML")

async def cmd_set_city(message: Message):
    # парсим /set_city Город
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /set_city <город>\nНапример: /set_city Санкт-Петербург")
        return

    city = parts[1].strip()

    async with async_session_maker() as session:
        user = await session.scalar(
            select(User).where(User.telegram_id == message.from_user.id)
        )

        if user is None:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                city=city,
            )
            session.add(user)
        else:
            user.city = city

        await session.commit()

    await message.answer(f"Окей, буду слать погоду для города: <b>{city}</b>", parse_mode="HTML")

def setup_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_set_city, Command(commands=["set_city"]))

async def main():
    logging.basicConfig(level=logging.INFO)

    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в переменных окружения")

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    setup_handlers(dp)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

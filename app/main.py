import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy import select

from .config import settings
from .db import engine, async_session_maker
from .models import Base, User

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
            # Обновим username, если вдруг изменился
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

async def cmd_set_city(message: Message):
    # парсим /set_city Город
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /set_city <город>\nНапример: /set_city Санкт-Петербург")
        return

    city = parts[1].strip()










def setup_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, CommandStart())


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

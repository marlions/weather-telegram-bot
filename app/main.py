import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from .config import settings


async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот для уведомлений о погоде 🌤\n\n"
        "Пока я умею только здороваться, "
        "но скоро появятся команды:\n"
        "/set_city - выбрать город\n"
        "/subscribe_daily - подписаться на ежедневные уведомления\n"
        "/unsubscribe - отписаться\n"
        "/current - текущая погода"
    )


def setup_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, CommandStart())


async def main():
    logging.basicConfig(level=logging.INFO)

    if not settings.telegram_bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN не задан в переменных окружения. "
            "Установи его перед запуском бота."
        )

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    setup_handlers(dp)

    # TODO: сюда позже добавим:
    #  - инициализацию БД
    #  - запуск планировщика уведомлений
    #  - регистрацию остальных хендлеров

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

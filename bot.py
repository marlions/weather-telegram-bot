import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import TOKEN
from handlers.common import register_common_handlers
from handlers.weather import register_weather_handlers

try:
    from app.http_client import HTTPClient
except Exception:
    HTTPClient = None

async def on_startup():
    if HTTPClient is None:
        return

    try:
        await HTTPClient.get_session()

    except Exception:
        pass


async def on_shutdown():
    if HTTPClient is None:
        return

    try:
        await HTTPClient.close()
    except Exception:
        pass


async def main():
    bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())

    register_common_handlers(dp)
    register_weather_handlers(dp)
    await dp.start_polling(bot, on_startup=on_startup, on_shutdown=on_shutdown)

if __name__ == "__main__":
    asyncio.run(main())

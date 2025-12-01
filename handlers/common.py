from aiogram import Router
from aiogram.types import Message

router = Router()

@router.message(commands=["start"])
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я погодный бот.\n"
        "Отправь название города, чтобы узнать погоду."
    )

def register_common_handlers(dp):
    dp.include_router(router)
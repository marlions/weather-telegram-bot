from aiogram import Router
from aiogram.types import Message
from services.weather_api import get_weather

router = Router()

@router.message()
async def get_weather_handler(message: Message):
    city = message.text.strip()
    if not city:
        return await message.answer("Введите название города.")

    weather = await get_weather(city)

    if weather is None:
        return await message.answer("Не удалось найти погоду для этого города.")

    text = (
        f"<b>{weather['city']}</b>\n"
        f"{weather['description']}\n"
        f"🌡 Температура: {weather['temp']}°C\n"
        f"💨 Ветер: {weather['wind']} м/с\n"
        f"💧 Влажность: {weather['humidity']}%"
    )

    await message.answer(text)


def register_weather_handlers(dp):
    dp.include_router(router)
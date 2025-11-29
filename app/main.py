import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select

from .config import settings
from .db import engine, async_session_maker
from .models import Base, User, Subscription
from .weather_client import get_current_weather, format_weather_message

class CityForm(StatesGroup):
    waiting_for_city = State()

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Текущая погода")],
            [KeyboardButton(text="Сменить город")],
            [KeyboardButton(text="Подписаться на прогноз")],
            [KeyboardButton(text="Отписаться от прогноза")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие…",
    )

async def btn_current(message: Message):
    await cmd_current(message)

async def btn_set_city(message: Message, state: FSMContext):
    await state.set_state(CityForm.waiting_for_city)
    await message.answer(
        "Введите новый город.\n\n"
        "Например: <code>Санкт-Петербург</code> или <code>London</code>",
        parse_mode="HTML",
    )

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
        "Можешь пользоваться командами или кнопками ниже.\n\n"
        "Доступные действия:\n"
        "• Текущая погода\n"
        "• Сменить город",
        reply_markup=main_menu_keyboard(),
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

async def process_city(message: Message, state: FSMContext):
    city = message.text.strip()
    if not city:
        await message.answer("Название города не должно быть пустым. Попробуйте ещё раз.")
        return

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

    await state.clear()

    await message.answer(
        f"Город обновлён на: <b>{city}</b>",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )

async def subscribe_daily(message: Message):
    async with async_session_maker() as session:
        user = await session.scalar(
            select(User).where(User.telegram_id == message.from_user.id)
        )

def setup_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_set_city, Command(commands=["set_city"]))
    dp.message.register(cmd_current, Command(commands=["current"]))
    dp.message.register(btn_current, F.text == "Текущая погода")
    dp.message.register(btn_set_city, F.text == "Сменить город")
    dp.message.register(process_city, CityForm.waiting_for_city)

async def main():
    logging.basicConfig(level=logging.INFO)

    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в переменных окружения")

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    setup_handlers(dp)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

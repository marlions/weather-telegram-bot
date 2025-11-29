import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
        if user is None:
            await message.answer("Сначала напишите /start, чтобы я вас запомнил.")
            return

        if not user.city:
            await message.answer(
                "Сначала задайте город через кнопку «Сменить город» или команду /set_city."
            )
            return

        sub = await session.scalar(
            select(Subscription).where(Subscription.user_id == user.id)
        )

        if sub is None:
            sub = Subscription(
                user_id=user.id,
                city=user.city,
                daily_notifications=True,
            )
            session.add(sub)
        else:
            sub.city = user.city
            sub.daily_notifications = True

        user.subscribed = True
        await session.commit()

    await message.answer(
        f"Вы подписались на ежедневный прогноз для города: <b>{user.city}</b> 🌤",
        parse_mode="HTML",
    )

async def unsubscribe_daily(message: Message):
    async with async_session_maker() as session:
        user = await session.scalar(
            select(User).where(User.telegram_id == message.from_user.id)
        )

        if user is None:
            await message.answer("Я вас ещё не знаю. Напишите /start.")
            return

        sub = await session.scalar(
            select(Subscription).where(Subscription.user_id == user.id)
        )

        if sub is None or not sub.daily_notifications:
            await message.answer("Вы и так не подписаны на ежедневный прогноз.")
            return

        sub.daily_notifications = False
        user.subscribed = False
        await session.commit()

    await message.answer("Вы отписались от ежедневных уведомлений о погоде.")

async def send_daily_weather(bot: Bot):
    async with async_session_maker() as session:
        result = await session.execute(
            select(User, Subscription)
            .join(Subscription, Subscription.user_id == User.id)
            .where(
                Subscription.daily_notifications == True,
                User.city.isnot(None),
            )
        )
        rows = result.all()

    if not rows:
        return

    users_by_city: dict[str, list[int]] = {}

    for user, sub in rows:
        city = user.city or sub.city
        if not city:
            continue
        users_by_city.setdefault(city, []).append(user.telegram_id)

    for city, chat_ids in users_by_city.items():
        try:
            data = await get_current_weather(city)
            text = "Ежедневный прогноз 🌤\n\n" + format_weather_message(city, data)
        except Exception as e:
            logging.exception(f"Не удалось получить погоду для города {city}: {e}")
            continue

        for chat_id in chat_ids:
            try:
                await bot.send_message(chat_id, text, parse_mode="HTML")
            except Exception as e:
                logging.exception(f"Не удалось отправить сообщение пользователю {chat_id}: {e}")

def setup_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_set_city, Command(commands=["set_city"]))
    dp.message.register(cmd_current, Command(commands=["current"]))
    dp.message.register(subscribe_daily, Command(commands=["subscribe_daily"]))
    dp.message.register(unsubscribe_daily, Command(commands=["unsubscribe"]))
    dp.message.register(btn_current, F.text == "Текущая погода")
    dp.message.register(btn_set_city, F.text == "Сменить город")
    dp.message.register(subscribe_daily, F.text == "Подписаться на прогноз")
    dp.message.register(unsubscribe_daily, F.text == "Отписаться от прогноза")
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

    scheduler = AsyncIOScheduler(timezone="UTC")

    scheduler.add_job(
        send_daily_weather,
        "cron",
        hour=6,
        minute=0,
        args=[bot],
        id="daily_weather_job",
        replace_existing=True,
    )
    scheduler.add_job(send_daily_weather, "interval", minutes=1, args=[bot])
    scheduler.start()

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

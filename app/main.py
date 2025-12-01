import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select, func
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import settings
from .db import engine, async_session_maker
from .models import Base, User, Subscription
from .weather_client import (
    format_single_forecast,
    format_weather_message,
    format_weekly_forecast,
    get_current_weather,
    get_daily_forecast,
)
from .alerts import check_extreme_weather

if not os.path.exists("logs"):
    os.makedirs("logs")

log_path = os.path.join(os.getcwd(), 'logs', 'app.log')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log"),
        logging.FileHandler(log_path)
    ]
)
logger = logging.getLogger(__name__)

DEFAULT_NOTIFICATION_TIME = "06:00"

class CityForm(StatesGroup):
    waiting_for_city = State()
class ForecastForm(StatesGroup):
    waiting_for_day = State()
class NotificationTimeForm(StatesGroup):
    waiting_for_time_choice = State()
    waiting_for_time = State()
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Текущая погода"), KeyboardButton(text="Погода на 5 дней")],
            [KeyboardButton(text="Прогноз на выбранный день")],
            [KeyboardButton(text="Сменить город")],
            [
                KeyboardButton(text="Подписаться на прогноз"),
                KeyboardButton(text="Отписаться от прогноза"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие…",
    )

def notification_time_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Ночью"),
                KeyboardButton(text="Утром"),
            ],
            [
                KeyboardButton(text="Днём"),
                KeyboardButton(text="Вечером"),
            ],
            [KeyboardButton(text="Своё время")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите время получения уведомлений",
    )

def forecast_day_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1"), KeyboardButton(text="2"), KeyboardButton(text="3")],
            [KeyboardButton(text="4"), KeyboardButton(text="5")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите день (1–5)",
    )


async def _get_user(message: Message) -> User | None:
    async with async_session_maker() as session:
        return await session.scalar(
            select(User).where(User.telegram_id == message.from_user.id)
        )


async def _ensure_user_with_city(message: Message) -> User | None:
    user = await _get_user(message)

    if user is None:
        await message.answer("Я ещё не знаю, кто ты. Напиши сначала /start.")
        return None

    if not user.city:
        await message.answer("Сначала задай город командой:\n/set_city <город>")
        return None

    return user

def normalize_time_input(raw_value: str) -> str | None:
    try:
        parsed = datetime.strptime(raw_value, "%H:%M")
    except ValueError:
        return None

    return parsed.strftime("%H:%M")

async def btn_current(message: Message):
    await cmd_current(message)

async def btn_set_city(message: Message, state: FSMContext):
    await state.set_state(CityForm.waiting_for_city)
    await message.answer(
        "Введите новый город.\n\n"
        "Например: <code>Санкт-Петербург</code> или <code>London</code>",
        parse_mode="HTML",
    )

async def btn_week_forecast(message: Message):
    user = await _ensure_user_with_city(message)

    if user is None or not user.city:
        return

    city = user.city

    try:
        daily, timezone_offset = await get_daily_forecast(city, 5)
        text = format_weekly_forecast(city, daily, timezone_offset)
        await message.answer(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
    except Exception as e:
        logger.exception(
            f"Error fetching weekly forecast for {city} for user {message.from_user.id}: {e}"
        )
        await message.answer(
            f"Не удалось получить прогноз на 5 дней: {e}",
            reply_markup=main_menu_keyboard(),
        )


async def btn_forecast_day(message: Message, state: FSMContext):
    user = await _ensure_user_with_city(message)

    if user is None or not user.city:
        return

    await state.set_state(ForecastForm.waiting_for_day)
    await message.answer(
        "На какой день показать прогноз? Выберите кнопку ниже (от 1 до 5).",
        reply_markup=forecast_day_keyboard(),
    )

async def cmd_start(message: Message):
    try:
        logger.info(f"User start: {message.from_user.id} / {message.from_user.username}")
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
                await session.commit()  # commit after adding the new user
            else:
                user.username = message.from_user.username
                await session.commit()  # commit after updating the user

            await message.answer(
                "Привет! Я бот для уведомлений о погоде 🌤\n\n"
                "Можешь пользоваться командами или кнопками ниже.\n\n"
                "Доступные действия:\n"
                "• Текущая погода\n"
                "• Прогноз на выбранный день\n"
                "• Погода на 5 дней\n"
                "• Сменить город\n"
                "• Настроить время уведомлений\n"
                "• Подписаться на прогноз\n"
                "• Отписаться от прогноза",
                reply_markup=main_menu_keyboard(),
            )
            logger.info(f"/start handled successfully for {message.from_user.id}")
    except Exception as e:
        logger.exception(f"Error in /start handler for user {message.from_user.id}: {e}")
        await message.answer("Произошла ошибка, попробуйте позже.")

async def cmd_current(message: Message):
    user = await _ensure_user_with_city(message)

    if user is None or not user.city:
        return

    city = user.city

    try:
        logger.info(f"Fetching weather for {city} for user {message.from_user.id}")
        data = await get_current_weather(city)
        text = format_weather_message(city, data)
        await message.answer(text, parse_mode="HTML")

        logger.info(f"Successfully sent weather for {city} to user {message.from_user.id}")
    except Exception as e:
        logger.exception(f"Error fetching weather for {city} for user {message.from_user.id}: {e}")
        await message.answer(f"Не получилось получить погоду: {e}")

async def process_forecast_day(message: Message, state: FSMContext):
    choice = message.text.strip()

    if choice == "⬅️ Назад":
        await state.clear()
        await message.answer(
            "Вернул кнопку в главное меню.", reply_markup=main_menu_keyboard()
        )
        return

    if not choice.isdigit():
        await message.answer(
            "Пожалуйста, выберите число от 1 до 5.", reply_markup=forecast_day_keyboard()
        )
        return
    day_number = int(choice)

    if day_number < 1 or day_number > 5:
        await message.answer(
            "Доступны прогнозы только на 1–5 день. Попробуйте снова.",
            reply_markup=forecast_day_keyboard(),
        )
        return

    user = await _ensure_user_with_city(message)

    if user is None or not user.city:
        await state.clear()
        return

    city = user.city

    try:
        daily, timezone_offset = await get_daily_forecast(city, day_number)

        if len(daily) < day_number:
            await message.answer(
                "Сервис вернул недостаточно данных. Попробуйте позже.",
                reply_markup=main_menu_keyboard(),
            )
            await state.clear()
            return

        text = format_single_forecast(city, daily[day_number - 1], timezone_offset, day_number)
        await message.answer(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
    except Exception as e:
        logger.exception(
            f"Error fetching forecast for day {day_number} for {city} / {message.from_user.id}: {e}"
        )
        await message.answer(
            f"Не удалось получить прогноз: {e}", reply_markup=main_menu_keyboard()
        )
    finally:
        await state.clear()

async def set_notification_time_handler(message: Message, state: FSMContext):
    user = await _ensure_user_with_city(message)

    if user is None or not user.city:
        return

    notification_time = message.text.strip()

    if not notification_time:
        await message.answer(
            "Пожалуйста, введите время в формате ЧЧ:ММ.",
            reply_markup=notification_time_keyboard(),
        )
        return

    try:
        await save_notification_time(message, user.id, notification_time)
        await message.answer(
            f"Время уведомлений для города {user.city} установлено на: <b>{notification_time}</b>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )
        await state.clear()
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}. Попробуйте снова.")
        await state.clear()

async def cmd_set_city(message: Message, new_city=None):
    try:
        logger.info(f"Setting city for user {message.from_user.id}: {new_city}")
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Использование: /set_city <город>\nНапример: /set_city Санкт-Петербург")
            return

        city = parts[1].strip()

        if not city:
            await message.answer("Город не может быть пустым. Попробуйте ещё раз.")
            return

        try:
            await get_current_weather(city)
        except Exception as e:
            await message.answer(f"Не удалось найти город: {city}. Проверьте правильность написания.")
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

        await message.answer(f"Окей, буду слать погоду для города: <b>{city}</b>", parse_mode="HTML")
        logger.info(f"City for user {message.from_user.id} set to {city}")
    except Exception as e:
        logger.exception(f"Error in /set_city for user {message.from_user.id}: {e}")
        await message.answer("Не удалось сохранить город.")

async def process_city(message: Message, state: FSMContext):
    city = message.text.strip()
    if not city:
        await message.answer("Название города не должно быть пустым. Попробуйте ещё раз.")
        return
    try:
        await get_current_weather(city)
    except Exception as e:
        await message.answer(f"Не удалось найти город: {city}. Проверьте правильность написания.")
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

async def subscribe_daily(message: Message, state: FSMContext):
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

    await message.answer(
        "Выберите время получения уведомлений", reply_markup=notification_time_keyboard()
    )
    await state.set_state(NotificationTimeForm.waiting_for_time_choice)
    logger.info(f"User {message.from_user.id} started subscription flow")

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

async def ask_notification_time(message: Message, state: FSMContext):
    user = await _ensure_user_with_city(message)

    if user is None:
        return

    await state.set_state(NotificationTimeForm.waiting_for_time)
    await message.answer(
        "Введите время для ежедневных уведомлений в формате <b>ЧЧ:ММ</b> (UTC).",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="⬅️ Назад")]],
            resize_keyboard=True,
            input_field_placeholder="Напишите время или вернитесь назад",
        ),
    )

async def save_notification_time(session, user_id: int, notification_time: str):
    normalized_time = notification_time.strip()
    subscription = await session.scalar(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    if subscription:
        subscription.notification_time = normalized_time
    else:
        subscription = Subscription(
            user_id=user_id,
            notification_time=normalized_time,
            daily_notifications=True
        )
        session.add(subscription)
    await session.commit()

async def process_notification_time(message: Message, state: FSMContext):
    time_input = message.text.strip()

    if time_input == "⬅️ Назад":
        await state.set_state(NotificationTimeForm.waiting_for_time_choice)
        await message.answer(
            "Хорошо, выберите время уведомлений заново.",
            reply_markup=notification_time_keyboard(),
        )
        return

    normalized_time = normalize_time_input(time_input)

    if normalized_time is None:
        await message.answer(
            "Не удалось распознать время. Используйте формат ЧЧ:ММ, например 08:30.",
            reply_markup=notification_time_keyboard(),
        )
        return

    async with async_session_maker() as session:
        await save_notification_time(session, message.from_user.id, normalized_time)

    await state.clear()
    await message.answer(
        f"Время уведомлений сохранено: <b>{normalized_time}</b>. "
        "Подпишитесь на прогноз, чтобы получать сообщения.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )

    user = await _ensure_user_with_city(message)

    if user is None:
        await state.clear()
        return

    async with async_session_maker() as session:
        db_user = await session.scalar(select(User).where(User.telegram_id == user.telegram_id))

        if db_user is None:
            await message.answer("Сначала напишите /start, чтобы я вас запомнил.")
            await state.clear()
            return

        subscription = await session.scalar(
            select(Subscription).where(Subscription.user_id == db_user.id)
        )

        if subscription is None:
            subscription = Subscription(
                user_id=db_user.id,
                city=db_user.city or "",
                daily_notifications=True,
                notification_time=normalized_time,
            )
            session.add(subscription)
        else:
            subscription.notification_time = normalized_time
            subscription.daily_notifications = True
            if db_user.city:
                subscription.city = db_user.city
        db_user.subscribed = True
        await session.commit()

    await state.clear()

    if subscription.daily_notifications:
        text = (
            f"Буду присылать ежедневные уведомления в <b>{normalized_time}</b> (UTC)."
        )
    else:
        text = (
            f"Время уведомлений сохранено: <b>{normalized_time}</b>. "
            "Подпишитесь на прогноз, чтобы получать сообщения."
        )

    await message.answer(text, parse_mode="HTML", reply_markup=main_menu_keyboard())


async def process_notification_choice(message: Message, state: FSMContext):
    user = await _ensure_user_with_city(message)

    if not user or not user.city:
        await message.answer("Не удалось найти ваш город. Пожалуйста, настройте город.",
                             reply_markup=main_menu_keyboard())
        return
    choice = message.text.strip()
    preset_times = {
        "Ночью": "00:30",
        "Утром": "06:00",
        "Днём": "12:00",
        "Вечером": "18:00",
    }

    if choice == "⬅️ Назад":
        await state.clear()
        await message.answer("Возвращаюсь в главное меню.", reply_markup=main_menu_keyboard())
        return

    if choice == "Своё время":
        await ask_notification_time(message, state)
        return

    if choice not in preset_times:
        await message.answer(
            "Пожалуйста, выберите один из предложенных вариантов.",
            reply_markup=notification_time_keyboard(),
        )
        return

    normalized_time = preset_times[choice]

    async with async_session_maker() as session:
        await save_notification_time(session, user.id, normalized_time)

    await message.answer(
        f"Вы подписались на ежедневный прогноз для города: <b>{user.city}</b> 🌤\n"
        f"Время уведомлений: <b>{normalized_time}</b> (UTC)",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )

    async with async_session_maker() as session:
        db_user = await session.scalar(
            select(User).where(User.telegram_id == message.from_user.id)
        )

        if db_user is None:
            await message.answer("Сначала напишите /start, чтобы я вас запомнил.")
            await state.clear()
            return

        subscription = await session.scalar(
            select(Subscription).where(Subscription.user_id == db_user.id)
        )

        if subscription is None:
            subscription = Subscription(
                user_id=db_user.id,
                city=db_user.city or "",
                daily_notifications=True,
                notification_time=normalized_time,
            )
            session.add(subscription)
        else:
            subscription.notification_time = normalized_time
            subscription.daily_notifications = True
            if db_user.city:
                subscription.city = db_user.city

        db_user.subscribed = True
        await session.commit()

    await state.clear()
    await message.answer(
        f"Вы подписались на ежедневный прогноз для города: <b>{db_user.city}</b> 🌤\n"
        f"Время уведомлений: <b>{normalized_time}</b> (UTC)",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )

    logger.info(
        f"User {message.from_user.id} subscribed to daily weather updates for {db_user.city} at {normalized_time}"
    )


async def send_daily_weather(bot: Bot, current_time: str | None = None):
    try:
        target_time = current_time or datetime.utcnow().strftime("%H:%M")
        logger.info(f"Starting daily weather broadcast for {target_time}")
        async with async_session_maker() as session:
            result = await session.execute(
                select(User, Subscription)
                .join(Subscription, Subscription.user_id == User.id)
                .where(
                    Subscription.daily_notifications == True,
                    User.city.isnot(None),
                    func.coalesce(
                        Subscription.notification_time.cast(func.VARCHAR),
                        DEFAULT_NOTIFICATION_TIME
                    )
                    == target_time,
                )
            )
            rows = result.all()

            filtered_rows = [
                (user, sub)
                for user, sub in rows
                if (sub.notification_time or DEFAULT_NOTIFICATION_TIME) == target_time
            ]

            if not filtered_rows:
                return

        users_by_city: dict[str, list[int]] = {}

        for user, sub in filtered_rows:
            city = user.city or sub.city
            if not city:
                continue
            users_by_city.setdefault(city, []).append(user.telegram_id)

        for city, chat_ids in users_by_city.items():
            try:
                data = await get_current_weather(city)
                daily_text = "Ежедневный прогноз 🌤\n\n" + format_weather_message(city, data)
                alert_text = check_extreme_weather(data)
            except Exception as e:
                logger.exception(f"Не удалось получить погоду для города {city}: {e}")
                continue

            for chat_id in chat_ids:
                try:
                    await bot.send_message(chat_id, daily_text, parse_mode="HTML")
                except Exception as e:
                    logger.exception(f"Не удалось отправить ежедневный прогноз пользователю {chat_id}: {e}")

            if alert_text:
                for chat_id in chat_ids:
                    try:
                        await bot.send_message(chat_id, alert_text, parse_mode="HTML")
                    except Exception as e:
                        logger.exception(f"Не удалось отправить экстренное предупреждение пользователю {chat_id}: {e}")
        logger.info("Daily weather broadcast succeeded")
    except Exception as e:
        logger.exception(f"Error in daily weather broadcast: {e}")

async def cmd_help(message: Message):
    help_text = """
    Привет! Я бот для получения прогноза погоды. Вот что я могу:

    - /current — Текущая погода в выбранном городе.
    - /set_city <город> — Установить город для прогнозов.
    - /set_notification_time <ЧЧ:ММ> — Установить время ежедневных уведомлений.
    - Кнопки для прогноза на выбранный день и на 5 дней.
    - Подписка на ежедневные прогнозы (через кнопки).
    - Экстренные уведомления при критичных погодных условиях.

    Просто нажмите кнопку или введите команду.
    """
    await message.answer(help_text)

if not os.path.exists('logs'):
    os.makedirs('logs')

def setup_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_set_city, Command(commands=["set_city"]))
    dp.message.register(cmd_current, Command(commands=["current"]))
    dp.message.register(subscribe_daily, Command(commands=["subscribe_daily"]))
    dp.message.register(ask_notification_time, Command(commands=["set_notification_time", "set_notify_time"]))
    dp.message.register(unsubscribe_daily, Command(commands=["unsubscribe"]))
    dp.message.register(cmd_help, Command(commands=["help"]))
    dp.message.register(btn_current, F.text == "Текущая погода")
    dp.message.register(btn_week_forecast, F.text == "Погода на 5 дней")
    dp.message.register(btn_forecast_day, F.text == "Прогноз на выбранный день")
    dp.message.register(btn_set_city, F.text == "Сменить город")
    dp.message.register(subscribe_daily, F.text == "Подписаться на прогноз")
    dp.message.register(unsubscribe_daily, F.text == "Отписаться от прогноза")
    dp.message.register(process_city, StateFilter(CityForm.waiting_for_city))
    dp.message.register(
        process_forecast_day, StateFilter(ForecastForm.waiting_for_day)
    )
    dp.message.register(
        process_notification_choice,
        StateFilter(NotificationTimeForm.waiting_for_time_choice),
    )
    dp.message.register(
        process_notification_time, StateFilter(NotificationTimeForm.waiting_for_time)
    )

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
        minute="*",
        args=[bot],
        id="daily_weather_job",
        replace_existing=True,
    )
    scheduler.start()

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

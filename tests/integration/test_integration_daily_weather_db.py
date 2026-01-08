import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import app.main as main_module
from app.db import DATABASE_URL
from app.models import Base, Subscription, User

pytestmark = pytest.mark.integration


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id, text, parse_mode=None):
        self.messages.append(
            {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        )


def _get_test_database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL") or DATABASE_URL

    if "weather-postgres" in url and os.getenv("RUNNING_IN_DOCKER") != "1":
        url = url.replace("weather-postgres", os.getenv("TEST_DB_HOST", "localhost"))

    return url


@pytest.mark.asyncio
async def test_send_daily_weather_uses_real_postgres(monkeypatch):
    if os.getenv("RUN_INTEGRATION_TESTS") != "1":
        pytest.skip("Integration test skipped (set RUN_INTEGRATION_TESTS=1 to run)")

    db_url = _get_test_database_url()

    engine = create_async_engine(db_url, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        await engine.dispose()
        pytest.skip(f"Postgres is not available for integration test: {exc!r}")

    async with Session() as s:
        await s.execute(text("TRUNCATE TABLE subscriptions RESTART IDENTITY CASCADE"))
        await s.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
        await s.commit()

    async with Session() as s:
        user = User(
            telegram_id=123456789,
            username="integration_user",
            city="Тестоград",
            subscribed=True,
        )
        s.add(user)
        await s.flush()

        sub = Subscription(
            user_id=user.id,
            city=user.city,
            daily_notifications=True,
            notification_time=main_module.DEFAULT_NOTIFICATION_TIME,
        )
        s.add(sub)
        await s.commit()

    monkeypatch.setattr(main_module, "async_session_maker", Session)

    async def fake_get_current_weather(city: str, client=None):
        return {
            "main": {"temp": -22.0, "feels_like": -25.0, "humidity": 80},
            "wind": {"speed": 16.0},
            "weather": [{"description": "гроза и штормовой ветер"}],
        }

    monkeypatch.setattr(main_module, "get_current_weather", fake_get_current_weather)

    bot = FakeBot()
    await main_module.send_daily_weather(
        bot, current_time=main_module.DEFAULT_NOTIFICATION_TIME
    )

    assert bot.messages, "Должны быть отправлены сообщения подписчику"
    joined = "\n---\n".join(m["text"] for m in bot.messages)

    assert "Ежедневный прогноз" in joined
    assert ("Экстренное предупреждение" in joined) or ("⚠️" in joined)

    await engine.dispose()

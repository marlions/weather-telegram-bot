import pytest
from sqlalchemy import delete

from app.db import async_session_maker, engine
from app.models import Base, User, Subscription
from app.main import send_daily_weather


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id, text, parse_mode=None):
        self.messages.append(
            {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        )
@pytest.mark.asyncio
async def test_daily_weather_flow(monkeypatch):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        await session.execute(delete(Subscription))
        await session.execute(delete(User))
        await session.commit()

        user = User(
            telegram_id=123456,
            username="testuser",
            city="Тестоград",
            subscribed=True,
        )
        session.add(user)
        await session.flush()

        sub = Subscription(
            user_id=user.id,
            city=user.city,
            daily_notifications=True,
        )
        session.add(sub)
        await session.commit()

    async def fake_get_current_weather(city: str):
        return {
            "main": {
                "temp": -22.0,
                "feels_like": -25.0,
                "humidity": 80,
            },
            "wind": {"speed": 10.0},
            "weather": [{"description": "сильный снегопад"}],
        }

    import app.main as main_module
    monkeypatch.setattr(main_module, "get_current_weather", fake_get_current_weather)

    fake_bot = FakeBot()

    await send_daily_weather(fake_bot)

    msgs = [m for m in fake_bot.messages if m["chat_id"] == 123456]
    assert msgs, "Должны быть отправлены сообщения подписчику"

    text_all = "\n---\n".join(m["text"] for m in msgs)

    assert "Ежедневный прогноз" in text_all
    assert ("Экстренное предупреждение" in text_all) or ("⚠️" in text_all)
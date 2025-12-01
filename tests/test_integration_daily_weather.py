import pytest
from app.models import User, Subscription
from app.main import DEFAULT_NOTIFICATION_TIME, send_daily_weather

class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id, text, parse_mode=None):
        self.messages.append(
            {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        )

class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

class FakeSession:
    def __init__(self, rows):
        self._rows = rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, *args, **kwargs):
        return FakeResult(self._rows)

class FakeSessionMaker:
    def __init__(self, rows):
        self._rows = rows

    def __call__(self):
        return FakeSession(self._rows)

@pytest.mark.asyncio
async def test_daily_weather_flow(monkeypatch):
    user = User(
        id=1,
        telegram_id=123456,
        username="testuser",
        city="Тестоград",
        subscribed=True,
    )
    sub = Subscription(
        user_id=user.id,
        city=user.city,
        daily_notifications=True,
    )

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
    monkeypatch.setattr(
        main_module,
        "async_session_maker",
        FakeSessionMaker([(user, sub)]),
    )

    fake_bot = FakeBot()

    await send_daily_weather(fake_bot, current_time=DEFAULT_NOTIFICATION_TIME)

    msgs = [m for m in fake_bot.messages if m["chat_id"] == 123456]
    assert msgs, "Должны быть отправлены сообщения подписчику"

    text_all = "\n---\n".join(m["text"] for m in msgs)

    assert "Ежедневный прогноз" in text_all
    assert ("Экстренное предупреждение" in text_all) or ("⚠️" in text_all)
    assert "Температура: <b>-22.0°C</b>" in text_all
    assert "Ощущается как: <b>-25.0°C</b>" in text_all
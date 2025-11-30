import pytest

import app.main as main_module
from app.models import Subscription, User


class FakeSelect:
    def __init__(self, *models):
        self.models = models

    def where(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

class FakeSession:
    def __init__(self, user: User, subscription: Subscription | None = None):
        self.user = user
        self.subscription = subscription

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def scalar(self, query):
        if query.models == (main_module.User,):
            return self.user
        if query.models == (main_module.Subscription,):
            return self.subscription
        return None

    def add(self, obj):
        if isinstance(obj, Subscription):
            self.subscription = obj
        if isinstance(obj, User):
            self.user = obj

    async def commit(self):
        return None

    async def execute(self, query):
        if query.models == (main_module.User, main_module.Subscription):
            rows = []
            if self.subscription and self.subscription.daily_notifications:
                rows.append((self.user, self.subscription))
            return FakeResult(rows)
        return FakeResult([])

class FakeSessionMaker:
    def __init__(self, user: User, subscription: Subscription | None = None):
        self.user = user
        self.subscription = subscription

    def __call__(self):
        return FakeSession(self.user, self.subscription)


class FakeMessage:
    def __init__(self, text: str, telegram_id: int, username: str | None = None):
        self.text = text
        self.from_user = type("FromUser", (), {"id": telegram_id, "username": username})
        self.responses: list[dict[str, str]] = []

    async def answer(self, text: str, parse_mode: str | None = None, reply_markup=None):
        self.responses.append({"text": text, "parse_mode": parse_mode})


class FakeBot:
    def __init__(self):
        self.messages: list[dict[str, str | int]] = []

    async def send_message(self, chat_id, text, parse_mode=None):
        self.messages.append({"chat_id": chat_id, "text": text, "parse_mode": parse_mode})

@pytest.mark.asyncio
async def test_update_city_persists_and_used_for_requests(monkeypatch):
    user = User(id=1, telegram_id=100, username="tester", city="Старый", subscribed=True)
    subscription = Subscription(user_id=user.id, city=user.city, daily_notifications=True)

    requested_cities: list[str] = []

    async def fake_get_current_weather(city: str):
        requested_cities.append(city)
        return {
            "main": {"temp": 5.0, "feels_like": 3.0},
            "weather": [{"description": "ясно"}],
        }

    monkeypatch.setattr(main_module, "get_current_weather", fake_get_current_weather)
    monkeypatch.setattr(main_module, "async_session_maker", FakeSessionMaker(user, subscription))
    monkeypatch.setattr(main_module, "select", lambda *models: FakeSelect(*models))

    message_set_city = FakeMessage("/set_city Новый", user.telegram_id, user.username)
    await main_module.cmd_set_city(message_set_city)

    assert user.city == "Новый"
    assert requested_cities == ["Новый"], "Для валидации должен использоваться новый город"

    message_current = FakeMessage("/current", user.telegram_id, user.username)
    await main_module.cmd_current(message_current)

    assert requested_cities == ["Новый", "Новый"], "Погодный запрос должен идти по новому городу"
    combined_responses = "\n".join(msg["text"] for msg in message_set_city.responses + message_current.responses)
    assert "Новый" in combined_responses
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
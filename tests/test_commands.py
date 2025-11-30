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
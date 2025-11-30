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
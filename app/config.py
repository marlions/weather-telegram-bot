import os
from dataclasses import dataclass


@dataclass
class Settings:
    telegram_bot_token: str


def get_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    return Settings(telegram_bot_token=token)


settings = get_settings()

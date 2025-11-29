import os
from dataclasses import dataclass

@dataclass
class Settings:
    telegram_bot_token: str
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: str

def get_settings() -> Settings:
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        postgres_user=os.getenv("POSTGRES_USER", "weather_user"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "weather_pass"),
        postgres_db=os.getenv("POSTGRES_DB", "weather_db"),
        postgres_host=os.getenv("POSTGRES_HOST", "weather-postgres"),
        postgres_port=os.getenv("POSTGRES_PORT", "5432"),
    )

settings = get_settings()

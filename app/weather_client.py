from typing import Any, Dict
import httpx
from .config import settings

class WeatherClientError(Exception):
    pass

async def get_current_weather(city: str) -> Dict[str, Any]:
    if not settings.openweather_api_key:
        raise WeatherClientError("API-ключ OpenWeatherMap не настроен")
    params = {
        "q": city,
        "appid": settings.openweather_api_key,
        "units": "metric",
        "lang": "ru",
    }

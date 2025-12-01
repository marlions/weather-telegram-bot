import os
from app.http_client import HTTPClient
from app.cache import get_cached, set_cached

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_KEY = os.getenv("OPEN_WEATHER_KEY")  # или OWM_KEY, как у тебя настроено

async def get_weather(city: str, units: str = "metric", ttl: int = 300):
    if not OWM_KEY:
        raise RuntimeError("OPEN_WEATHER_KEY not set")

    cache_key = f"weather:{city.strip().lower()}:{units}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    params = {"q": city, "appid": OWM_KEY, "units": units, "lang": "ru"}
    data = await HTTPClient.fetch_json(BASE_URL, params=params, timeout=10)
    if not data:
        return None

    result = {
        "city": data.get("name"),
        "temp": data.get("main", {}).get("temp"),
        "humidity": data.get("main", {}).get("humidity"),
        "wind": data.get("wind", {}).get("speed"),
        "description": (data.get("weather") or [{}])[0].get("description"),
    }

    await set_cached(cache_key, result, ttl=ttl)
    return result
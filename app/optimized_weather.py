import os
from .http_client import HTTPClient
from .cache import get_cached, set_cached

OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_KEY = os.getenv("OWM_KEY")

async def get_weather(city: str, units: str = "metric", ttl: int = 300):
    if not OWM_KEY:
        raise RuntimeError("OWM_KEY is not set in environment")

    city_key = city.strip().lower()
    cache_key = f"weather:{city_key}:{units}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    params = {"q": city, "appid": OWM_KEY, "units": units}
    data = await HTTPClient.fetch_json(OWM_URL, params=params, timeout=10)
    await set_cached(cache_key, data, ttl=ttl)
    return data
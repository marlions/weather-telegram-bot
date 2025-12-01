import os
from typing import Optional, Dict, Any

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_KEY = os.getenv("OPEN_WEATHER_KEY") or os.getenv("OWM_KEY") or os.getenv("OPENWEATHER_API_KEY")

try:
    from app.http_client import HTTPClient
except Exception:
    HTTPClient = None

try:
    from app.cache import get_cached, set_cached
except Exception:
    import asyncio, time, json

    _local_cache = {}
    _local_lock = asyncio.Lock()

    async def get_cached(key: str):
        async with _local_lock:
            item = _local_cache.get(key)
            if not item:
                return None
            ts, ttl, value = item
            if time.time() - ts > ttl:
                del _local_cache[key]
                return None
            return value

    async def set_cached(key: str, value, ttl: int = 300):
        async with _local_lock:
            _local_cache[key] = (time.time(), ttl, value)


async def _fetch_json_direct(url: str, params: dict, timeout: int = 10) -> Optional[Dict[str, Any]]:
    try:
        import aiohttp
    except Exception:
        return None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=timeout) as resp:
                resp.raise_for_status()
                return await resp.json()
    except Exception:
        return None


async def get_weather(city: str, units: str = "metric", ttl: int = 300) -> Optional[Dict[str, Any]]:
    if not OWM_KEY:
        raise RuntimeError("OPEN_WEATHER_KEY (or OWM_KEY / OPENWEATHER_API_KEY) is not set in environment")

    city_key = city.strip().lower()
    cache_key = f"weather:{city_key}:{units}"

    try:
        cached = await get_cached(cache_key)
    except Exception:
        cached = None

    if cached:
        return cached

    params = {"q": city, "appid": OWM_KEY, "units": units, "lang": "ru"}

    data = None
    if HTTPClient is not None:
        try:
            data = await HTTPClient.fetch_json(BASE_URL, params=params, timeout=10)
        except Exception:
            data = None

    if data is None:
        data = await _fetch_json_direct(BASE_URL, params=params, timeout=10)

    if not data:
        return None

    result = {
        "city": data.get("name"),
        "temp": data.get("main", {}).get("temp"),
        "humidity": data.get("main", {}).get("humidity"),
        "wind": data.get("wind", {}).get("speed"),
        "description": (data.get("weather") or [{}])[0].get("description"),
    }

    try:
        await set_cached(cache_key, result, ttl=ttl)
    except Exception:
        pass

    return result
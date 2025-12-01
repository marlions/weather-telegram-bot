import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

class WeatherClientError(Exception):
    pass

_geocode_cache: Dict[str, Tuple[float, float, float]] = {}
_GEOCODE_TTL_SECONDS = 60 * 60  # 1 hour


def _ensure_api_key() -> str:
    import os

    key = os.getenv("OPENWEATHER_API_KEY")
    if not key:
        raise WeatherClientError("OPENWEATHER_API_KEY is not set in environment")
    return key


async def _get_city_coordinates(city: str, client: Optional[httpx.AsyncClient] = None) -> Tuple[float, float]:
    now = time.time()
    cached = _geocode_cache.get(city.lower())
    if cached and cached[2] > now:
        return cached[0], cached[1]

    api_key = _ensure_api_key()
    params = {"q": city, "limit": 1, "appid": api_key}

    async def _fetch(c: httpx.AsyncClient) -> httpx.Response:
        return await c.get("http://api.openweathermap.org/geo/1.0/direct", params=params, timeout=10.0)

    if client is None:
        async with httpx.AsyncClient() as local_client:
            try:
                resp = await _fetch(local_client)
            except httpx.RequestError as e:
                raise WeatherClientError(f"Network error while geocoding '{city}': {e}") from e
    else:
        try:
            resp = await _fetch(client)
        except httpx.RequestError as e:
            raise WeatherClientError(f"Network error while geocoding '{city}': {e}") from e

    if resp.status_code != 200:
        raise WeatherClientError(f"Geocoding API returned {resp.status_code}: {resp.text}")

    arr = resp.json()
    if not arr:
        raise WeatherClientError(f"City '{city}' not found in geocoding API")

    lat = float(arr[0]["lat"])
    lon = float(arr[0]["lon"])
    _geocode_cache[city.lower()] = (lat, lon, now + _GEOCODE_TTL_SECONDS)
    return lat, lon


def _select_icon_for_condition(condition: str) -> str:
    c = (condition or "").lower()
    if "rain" in c or "drizzle" in c:
        return "🌧️"
    if "thunder" in c:
        return "⛈️"
    if "snow" in c:
        return "❄️"
    if "clear" in c:
        return "☀️"
    if "cloud" in c:
        return "☁️"
    if "mist" in c or "fog" in c or "haze" in c:
        return "🌫️"
    return "🌡️"


def _aggregate_daily(list_3h: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from collections import defaultdict, Counter
    import datetime

    days = defaultdict(list)
    for block in list_3h:
        ts = block.get("dt", 0)
        date = datetime.datetime.utcfromtimestamp(ts).date().isoformat()
        days[date].append(block)

    result = []
    for date, blocks in sorted(days.items()):
        temps = [b["main"]["temp"] for b in blocks if "main" in b and "temp" in b]
        mins = [b["main"].get("temp_min", b["main"]["temp"]) for b in blocks if "main" in b]
        maxs = [b["main"].get("temp_max", b["main"]["temp"]) for b in blocks if "main" in b]

        # condition most common by weather[0]['main'] or description
        conds = [b["weather"][0]["main"] if b.get("weather") else "" for b in blocks]
        cond_counter = Counter(conds)
        common_cond = cond_counter.most_common(1)[0][0] if cond_counter else ""

        precip = 0.0
        for b in blocks:
            if "rain" in b and isinstance(b["rain"], dict):
                precip += float(b["rain"].get("3h", 0.0))
            elif "snow" in b and isinstance(b["snow"], dict):
                precip += float(b["snow"].get("3h", 0.0))
            else:
                pop = float(b.get("pop", 0.0))
                precip += pop * 0.2

        if temps:
            result.append({
                "date": date,
                "min_temp": min(mins) if mins else min(temps),
                "max_temp": max(maxs) if maxs else max(temps),
                "condition": common_cond,
                "precip_mm": round(precip, 2),
            })
    return result


async def get_daily_forecast(city: str, client: Optional[httpx.AsyncClient] = None) -> Dict[str, Any]:

    api_key = _ensure_api_key()
    lat, lon = await _get_city_coordinates(city, client=client)

    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
        "exclude": "minutely,hourly,alerts,current",
    }

    url = "https://api.openweathermap.org/data/2.5/forecast"

    async def _fetch(c: httpx.AsyncClient) -> httpx.Response:
        return await c.get(url, params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}, timeout=15.0)

    if client is None:
        async with httpx.AsyncClient() as local_client:
            try:
                resp = await _fetch(local_client)
            except httpx.RequestError as e:
                raise WeatherClientError(f"Network error while fetching forecast for '{city}': {e}") from e
    else:
        try:
            resp = await _fetch(client)
        except httpx.RequestError as e:
            raise WeatherClientError(f"Network error while fetching forecast for '{city}': {e}") from e

    if resp.status_code != 200:
        raise WeatherClientError(f"Forecast API returned {resp.status_code}: {resp.text}")

    payload = resp.json()
    city_info = payload.get("city", {})
    raw_list = payload.get("list", [])
    daily = _aggregate_daily(raw_list)

    for d in daily:
        d["icon"] = _select_icon_for_condition(d.get("condition", ""))

    return {"city": city_info.get("name", city), "daily": daily}


async def get_current_weather(city: str, client: Optional[httpx.AsyncClient] = None) -> Dict[str, Any]:

    api_key = _ensure_api_key()
    params = {"q": city, "appid": api_key, "units": "metric"}

    async def _fetch(c: httpx.AsyncClient) -> httpx.Response:
        return await c.get("https://api.openweathermap.org/data/2.5/weather", params=params, timeout=10.0)

    if client is None:
        async with httpx.AsyncClient() as local_client:
            try:
                resp = await _fetch(local_client)
            except httpx.RequestError as e:
                raise WeatherClientError(f"Network error while fetching current weather for '{city}': {e}") from e
    else:
        try:
            resp = await _fetch(client)
        except httpx.RequestError as e:
            raise WeatherClientError(f"Network error while fetching current weather for '{city}': {e}") from e

    if resp.status_code == 404:
        raise WeatherClientError("City not found")
    if resp.status_code != 200:
        raise WeatherClientError(f"Weather API returned {resp.status_code}: {resp.text}")

    data = resp.json()
    return {
        "city": data.get("name", city),
        "temp": data.get("main", {}).get("temp"),
        "feels_like": data.get("main", {}).get("feels_like"),
        "condition": (data.get("weather") or [{}])[0].get("main", ""),
        "description": (data.get("weather") or [{}])[0].get("description", ""),
    }
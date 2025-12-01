from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Tuple, Optional
import httpx
from .config import settings

class WeatherClientError(Exception):
    pass

def _get_weather_icon(main: str | None = None, description: str | None = None) -> str:
    main_lower = main.lower() if main else ""
    description_lower = description.lower() if description else ""

    def contains(*keywords: str) -> bool:
        return any(keyword in description_lower for keyword in keywords)

    if main_lower == "thunderstorm" or contains("гроза", "thunder"):
        return "⛈️"
    if main_lower == "drizzle" or contains("морось", "drizzle"):
        return "🌦️"
    if main_lower == "rain" or contains("дожд", "ливень", "rain"):
        return "🌧️"
    if main_lower == "snow" or contains("снег", "snow"):
        return "❄️"
    if main_lower == "clear" or contains("ясно", "clear"):
        return "☀️"
    if contains("пасмур", "overcast"):
        return "☁️"
    if main_lower == "clouds" or contains("облач", "cloud"):
        return "🌥️"
    if main_lower in {"mist", "smoke", "haze"} or contains("туман", "дымка", "smog", "haze", "fog"):
        return "🌫️"
    if main_lower in {"dust", "sand", "ash"} or contains("пыль", "песок", "дым"):
        return "🏜️"
    if main_lower == "squall" or contains("шквал", "порыв"):
        return "🌬️"
    if main_lower == "tornado" or contains("торнадо"):
        return "🌪️"

    return "🌈"

def _ensure_api_key():
    if not settings.openweather_api_key:
        raise WeatherClientError("API-ключ OpenWeatherMap не настроен")
async def get_current_weather(city: str, client: Optional[httpx.AsyncClient] = None) -> Dict[str, Any]:
    _ensure_api_key()
    params = {
        "q": city,
        "appid": settings.openweather_api_key,
        "units": "metric",
        "lang": "ru",
    }
    if client is None:
        async with httpx.AsyncClient(timeout=10.0) as local_client:
            try:
                resp = await local_client.get("https://api.openweathermap.org/data/2.5/weather", params=params)
            except httpx.RequestError as e:
                raise WeatherClientError(f"Ошибка сети при запросе погоды: {e}") from e
    else:
        try:
            resp = await client.get("https://api.openweathermap.org/data/2.5/weather", params=params)
        except httpx.RequestError as e:
            raise WeatherClientError(f"Ошибка сети при запросе погоды: {e}") from e

    if resp.status_code == 404:
        raise WeatherClientError("Город не найден, проверьте написание")
    if resp.status_code != 200:
        raise WeatherClientError(f"Сервис погоды вернул ошибку: {resp.status_code} {resp.text}")

    return resp.json()

async def _get_city_coordinates(city: str) -> Tuple[float, float]:
    _ensure_api_key()

    params = {
        "q": city,
        "limit": 1,
        "appid": settings.openweather_api_key,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get("https://api.openweathermap.org/geo/1.0/direct", params=params)
        except httpx.RequestError as e:
            raise WeatherClientError(f"Ошибка сети при поиске города: {e}") from e

    if resp.status_code != 200:
        raise WeatherClientError(
            f"Сервис геокодирования вернул ошибку: {resp.status_code} {resp.text}"
        )

    data = resp.json()
    if not data:
        raise WeatherClientError("Город не найден, попробуйте уточнить запрос")

    lat = data[0].get("lat")
    lon = data[0].get("lon")

    if lat is None or lon is None:
        raise WeatherClientError("Не удалось определить координаты города")

    return float(lat), float(lon)

def _aggregate_daily(entries: List[Dict[str, Any]], timezone_offset: int) -> Dict[str, Any]:
    temps = [item.get("main", {}).get("temp") for item in entries if item.get("main")]
    temp_mins = [item["main"].get("temp_min") for item in entries if item.get("main")]
    temp_maxs = [item["main"].get("temp_max") for item in entries if item.get("main")]
    feels_like = [
        item.get("main", {}).get("feels_like") for item in entries if item.get("main")
    ]
    humidity = [
        item.get("main", {}).get("humidity") for item in entries if item.get("main")
    ]
    wind_speeds = [item.get("wind", {}).get("speed") for item in entries if item.get("wind")]
    descriptions: List[str] = []
    mains: List[str] = []
    for item in entries:
        for weather in item.get("weather", []):
            desc = weather.get("description")
            if desc:
                descriptions.append(desc)
            main = weather.get("main")
            if main:
                mains.append(main)

    dt = datetime.fromtimestamp(entries[0]["dt"] + timezone_offset, tz=timezone.utc)

    def _safe_avg(values: List[float]) -> float | None:
        filtered = [v for v in values if v is not None]
        if not filtered:
            return None
        return sum(filtered) / len(filtered)

    return {
        "date": dt.date(),
        "temp_min": min(temp_mins) if temp_mins else None,
        "temp_max": max(temp_maxs) if temp_maxs else None,
        "temp_avg": _safe_avg(temps),
        "feels_like_avg": _safe_avg(feels_like),
        "wind_speed_avg": _safe_avg(wind_speeds),
        "humidity_avg": _safe_avg(humidity),
        "main": Counter(mains).most_common(1)[0][0] if mains else None,
        "description": Counter(descriptions).most_common(1)[0][0]
        if descriptions
        else "нет данных",
    }

async def get_daily_forecast(city: str, days: int) -> Tuple[List[Dict[str, Any]], int]:
    if days < 1 or days > 5:
        raise ValueError("Количество дней должно быть в диапазоне 1-5")

    lat, lon = await _get_city_coordinates(city)

    params = {
        "lat": lat,
        "lon": lon,
        "units": "metric",
        "lang": "ru",
        "appid": settings.openweather_api_key,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get("https://api.openweathermap.org/data/2.5/forecast", params=params)
        except httpx.RequestError as e:
            raise WeatherClientError(f"Ошибка сети при запросе прогноза: {e}") from e

    if resp.status_code == 404:
        raise WeatherClientError("Город не найден, проверьте написание")
    if resp.status_code == 401:
        raise WeatherClientError(
            "API-ключ OpenWeatherMap недействителен."
        )

    if resp.status_code != 200:
        raise WeatherClientError(
            f"Сервис прогноза вернул ошибку: {resp.status_code} {resp.text}"
        )

    data = resp.json()
    forecast_list = data.get("list")
    if not forecast_list:
        raise WeatherClientError("Погодные данные недоступны для выбранного города")

    timezone_offset = data.get("city", {}).get("timezone", 0)
    grouped: defaultdict[date, List[Dict[str, Any]]] = defaultdict(list)

    for item in forecast_list:
        dt = datetime.fromtimestamp(item["dt"] + timezone_offset, tz=timezone.utc)
        grouped[dt.date()].append(item)

    sorted_dates = sorted(grouped.keys())
    aggregated = [_aggregate_daily(grouped[day], timezone_offset) for day in sorted_dates]

    return aggregated[:days], timezone_offset

def _format_date(day: date) -> str:
    return day.strftime("%d %b")

def _format_daily_block(day: Dict[str, Any], day_index: int) -> str:
    date_str = _format_date(day.get("date")) if day.get("date") else ""
    description = day.get("description", "нет данных")
    main_condition = day.get("main")
    icon = _get_weather_icon(main_condition, description)
    description_with_icon = f"{icon} {description.capitalize()}" if description else icon
    temp_min = day.get("temp_min")
    temp_max = day.get("temp_max")
    temp_avg = day.get("temp_avg")
    feels_like = day.get("feels_like_avg")
    wind_speed = day.get("wind_speed_avg")
    humidity = day.get("humidity_avg")

    parts = [f"{day_index}-й день ({date_str}): {description_with_icon}"]

    if temp_max is not None and temp_min is not None:
        parts.append(f"Диапазон: <b>{temp_min:.1f}°C</b> … <b>{temp_max:.1f}°C</b>")
    elif temp_avg is not None:
        parts.append(f"Температура: <b>{temp_avg:.1f}°C</b>")
    if feels_like is not None:
        parts.append(f"Ощущается в среднем как: <b>{feels_like:.1f}°C</b>")
    if humidity is not None:
        parts.append(f"Влажность: {humidity:.0f}%")
    if wind_speed is not None:
        parts.append(f"Ветер: {wind_speed:.1f} м/с")
    return "\n".join(parts)

def format_weekly_forecast(city: str, daily: List[Dict[str, Any]], timezone_offset: int) -> str:
    parts = [f"Погода на {len(daily)} дней в <b>{city}</b> 📅", ""]

    for index, day in enumerate(daily, start=1):
        parts.append(_format_daily_block(day, index))

    return "\n\n".join(parts)

def format_single_forecast(city: str, day: Dict[str, Any], timezone_offset: int, day_index: int) -> str:
    header = f"Прогноз на {day_index}-й день для <b>{city}</b> 📅"
    return "\n".join([header, "", _format_daily_block(day, day_index)])

def format_weather_message(city: str, data: Dict[str, Any]) -> str:
    main = data.get("main", {})
    weather_list = data.get("weather", [])
    wind = data.get("wind", {})

    temp = main.get("temp")
    feels = main.get("feels_like")
    humidity = main.get("humidity")
    description = weather_list[0]["description"] if weather_list else "нет данных"
    main_condition = weather_list[0].get("main") if weather_list else None
    wind_speed = wind.get("speed")
    icon = _get_weather_icon(main_condition, description)
    parts = [
        f"{icon} Погода в городе <b>{city}</b>",
        "",
        f"{description.capitalize()}",
    ]

    if temp is not None:
        parts.append(f"Температура: <b>{temp:.1f}°C</b>")
    if feels is not None:
        parts.append(f"Ощущается как: <b>{feels:.1f}°C</b>")
    if humidity is not None:
        parts.append(f"Влажность: {humidity}%")
    if wind_speed is not None:
        parts.append(f"Ветер: {wind_speed} м/с")
    return "\n".join(parts)
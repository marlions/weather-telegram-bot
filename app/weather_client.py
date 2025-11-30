from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
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
    async with httpx.AsyncClient(timeout=10.0) as client:
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
    if not settings.openweather_api_key:
        raise WeatherClientError("API-ключ OpenWeatherMap не настроен")

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
        raise WeatherClientError("Город не найден, проверьте написание")

    lat = data[0].get("lat")
    lon = data[0].get("lon")

    if lat is None or lon is None:
        raise WeatherClientError("Не удалось определить координаты города")

    return float(lat), float(lon)

async def get_daily_forecast(city: str, days: int) -> Tuple[List[Dict[str, Any]], int]:
    if days < 1 or days > 7:
        raise ValueError("Количество дней должно быть в диапазоне 1-7")

    lat, lon = await _get_city_coordinates(city)

    params = {
        "lat": lat,
        "lon": lon,
        "exclude": "minutely,hourly,alerts",
        "units": "metric",
        "lang": "ru",
        "appid": settings.openweather_api_key,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get("https://api.openweathermap.org/data/2.5/onecall", params=params)
        except httpx.RequestError as e:
            raise WeatherClientError(f"Ошибка сети при запросе прогноза: {e}") from e

    if resp.status_code != 200:
        raise WeatherClientError(
            f"Сервис прогноза вернул ошибку: {resp.status_code} {resp.text}"
        )

    data = resp.json()
    daily = data.get("daily")
    if not daily:
        raise WeatherClientError("Погодные данные недоступны для выбранного города")

    timezone_offset = data.get("timezone_offset", 0)

    return daily[:days], timezone_offset

def _format_date(timestamp: int, timezone_offset: int) -> str:
    if timestamp is None:
        return ""

    dt = datetime.fromtimestamp(timestamp + timezone_offset, tz=timezone.utc)
    return dt.strftime("%d %b")

def _format_daily_block(day: Dict[str, Any], timezone_offset: int, day_index: int) -> str:
    date_str = _format_date(day.get("dt"), timezone_offset)
    description = day.get("weather", [{}])[0].get("description", "нет данных").capitalize()
    temp = day.get("temp", {})
    temp_day = temp.get("day")
    temp_night = temp.get("night")
    feels_like = day.get("feels_like", {}).get("day")
    wind_speed = day.get("wind_speed")
    humidity = day.get("humidity")

    parts = [f"{day_index}-й день ({date_str}): {description}"]

    if temp_day is not None:
        parts.append(f"Днём: <b>{temp_day:.1f}°C</b>")
    if temp_night is not None:
        parts.append(f"Ночью: <b>{temp_night:.1f}°C</b>")
    if feels_like is not None:
        parts.append(f"Ощущается как: <b>{feels_like:.1f}°C</b>")
    if humidity is not None:
        parts.append(f"Влажность: {humidity}%")
    if wind_speed is not None:
        parts.append(f"Ветер: {wind_speed} м/с")

    return "\n".join(parts)

def format_weekly_forecast(city: str, daily: List[Dict[str, Any]], timezone_offset: int) -> str:
    parts = [f"Погода на {len(daily)} дней в <b>{city}</b> 📅", ""]

    for index, day in enumerate(daily, start=1):
        parts.append(_format_daily_block(day, timezone_offset, index))

    return "\n\n".join(parts)

def format_single_forecast(city: str, day: Dict[str, Any], timezone_offset: int, day_index: int) -> str:
    header = f"Прогноз на {day_index}-й день для <b>{city}</b> 📅"
    return "\n".join([header, "", _format_daily_block(day, timezone_offset, day_index)])

def format_weather_message(city: str, data: Dict[str, Any]) -> str:
    main = data.get("main", {})
    weather_list = data.get("weather", [])
    wind = data.get("wind", {})

    temp = main.get("temp")
    feels = main.get("feels_like")
    humidity = main.get("humidity")
    description = weather_list[0]["description"] if weather_list else "нет данных"
    wind_speed = wind.get("speed")

    parts = [
        f"Погода в городе <b>{city}</b> 🌤",
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
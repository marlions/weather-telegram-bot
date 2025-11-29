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
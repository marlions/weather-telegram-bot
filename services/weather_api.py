import aiohttp
from config import OPEN_WEATHER_KEY

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

async def get_weather(city: str):
    params = {
        "q": city,
        "appid": OPEN_WEATHER_KEY,
        "units": "metric",
        "lang": "ru"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(BASE_URL, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()

                return {
                    "city": data.get("name"),
                    "temp": data["main"].get("temp"),
                    "humidity": data["main"].get("humidity"),
                    "wind": data["wind"].get("speed"),
                    "description": data["weather"][0].get("description"),
                }
        except Exception:
            return None
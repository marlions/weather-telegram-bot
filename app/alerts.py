from typing import Any, Dict

def check_extreme_weather(data: Dict[str, Any]) -> str | None:
    main = data.get("main", {})
    weather_list = data.get("weather", [])
    wind = data.get("wind", {})

    temp = main.get("temp")
    feels = main.get("feels_like")
    wind_speed = wind.get("speed")
    description = (weather_list[0]["description"]
                   if weather_list else "").lower()

    reasons: list[str] = []
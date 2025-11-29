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

    if temp is not None:
        if temp <= -20:
            reasons.append("очень сильный мороз")
        elif temp <= -15:
            reasons.append("сильный мороз")
        elif temp >= 35:
            reasons.append("очень сильная жара")
        elif temp >= 30:
            reasons.append("жара")

    if feels is not None:
        if feels <= -25:
            reasons.append("экстремально низкая температура по ощущениям")

    if wind_speed is not None and wind_speed >= 15:
        reasons.append("очень сильный ветер")

    storm_keywords = ["гроза", "шторм", "буря", "snowstorm", "thunderstorm"]
    if any(word in description for word in storm_keywords):
        reasons.append("штормовые погодные условия")

    if not reasons:
        return None

    text_lines = [
        "⚠️ <b>Экстренное предупреждение о погоде</b>",
        "",
        "Обнаружены опасные погодные условия:",
    ]
    for r in reasons:
        text_lines.append(f"• {r}")

    text_lines.append("")
    text_lines.append("Рекомендуется быть осторожнее и по возможности ограничить время на улице.")

    return "\n".join(text_lines)
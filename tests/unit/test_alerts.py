from app.alerts import check_extreme_weather

def test_check_extreme_weather_returns_none_for_normal_weather():
    data = {
        "main": {
            "temp": 10.0,
            "feels_like": 8.0,
            "humidity": 70,
        },
        "wind": {
            "speed": 3.0,
        },
        "weather": [
            {"description": "облачно с прояснениями"},
        ],
    }

    result = check_extreme_weather(data)
    assert result is None, "Для обычной погоды не должно быть экстренного предупреждения"

def test_check_extreme_weather_detects_severe_frost():
    data = {
        "main": {
            "temp": -22.0,
            "feels_like": -28.0,
            "humidity": 80,
        },
        "wind": {
            "speed": 4.0,
        },
        "weather": [
            {"description": "ясно"},
        ],
    }
    result = check_extreme_weather(data)

    assert result is not None, "Для сильного мороза должно быть предупреждение"
    assert "мороз" in result.lower() or "низкая температура" in result.lower()

def test_check_extreme_weather_detects_storm_and_wind():
    data = {
        "main": {
            "temp": 5.0,
            "feels_like": 0.0,
            "humidity": 90,
        },
        "wind": {
            "speed": 18.0,
        },
        "weather": [
            {"description": "гроза и штормовой ветер"},
        ],
    }

    result = check_extreme_weather(data)

    assert result is not None
    text_lower = result.lower()
    assert "ветер" in text_lower or "шторм" in text_lower
    assert "⚠️" in result
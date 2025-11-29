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
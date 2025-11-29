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
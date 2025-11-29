from app.weather_client import format_weather_message

def test_format_weather_message_basic():
    city = "Санкт-Петербург"
    data = {
        "main": {
            "temp": 1.7,
            "feels_like": -2.8,
            "humidity": 94,
        },
        "wind": {
            "speed": 5.0,
        },
        "weather": [
            {"description": "облачно с прояснениями"},
        ],
    }
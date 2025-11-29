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

    text = format_weather_message(city, data)
    assert "Погода в городе" in text
    assert city in text
    assert "🌤" in text

    assert "Облачно с прояснениями" in text

    assert "Температура: <b>1.7°C</b>" in text

    assert "Ощущается как: -2.8°C" in text

    assert "Влажность: 94%" in text
    assert "Ветер: 5.0 м/с" in text

def test_format_weather_message_handles_missing_fields():
    city = "Тестоград"
    data = {
        "weather": [],
    }

    text = format_weather_message(city, data)
    assert city in text
    assert "Температура" not in text
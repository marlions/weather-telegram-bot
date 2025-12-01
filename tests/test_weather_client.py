import pytest
import httpx
from datetime import date
from unittest.mock import patch

from app import weather_client
from app.weather_client import get_current_weather, WeatherClientError


class MockAsyncClient:
    def __init__(self, response: httpx.Response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *args, **kwargs):
        return self._response


def mock_async_client(response: httpx.Response):
    def _client_factory(*args, **kwargs):
        return MockAsyncClient(response)
    return _client_factory


@pytest.fixture(autouse=True)
def mock_api_key():
    original_key = weather_client.settings.openweather_api_key
    weather_client.settings.openweather_api_key = "test-key"
    try:
        yield
    finally:
        weather_client.settings.openweather_api_key = original_key

@pytest.mark.asyncio
async def test_valid_city():
    response = httpx.Response(
        status_code=200,
        json={
            "weather": [{"description": "clear sky"}],
            "main": {"temp": 20.0},
            "name": "Saint Petersburg",
        },
        request=httpx.Request("GET", "https://api.openweathermap.org/data/2.5/weather"),
    )
    with patch("httpx.AsyncClient", mock_async_client(response)):
        result = await get_current_weather("Saint Petersburg")
    assert result["weather"][0]["description"] == "clear sky"
    assert result["main"]["temp"] == 20.0
    assert result["name"] == "Saint Petersburg"

@pytest.mark.asyncio
async def test_invalid_city():
    response = httpx.Response(
        status_code=404,
        json={},
        request=httpx.Request("GET", "https://api.openweathermap.org/data/2.5/weather"),
    )
    with patch("httpx.AsyncClient", mock_async_client(response)):
        with pytest.raises(WeatherClientError):
            await get_current_weather("InvalidCity")

@pytest.mark.asyncio
async def test_weather_api_error():
    response = httpx.Response(
        status_code=500,
        json={"message": "Server error"},
        request=httpx.Request("GET", "https://api.openweathermap.org/data/2.5/weather"),
    )
    with patch("httpx.AsyncClient", mock_async_client(response)):
        with pytest.raises(WeatherClientError):
            await get_current_weather("Saint Petersburg")

@pytest.mark.asyncio
async def test_request_error_handled(monkeypatch):
    request = httpx.Request("GET", "https://api.openweathermap.org/data/2.5/weather")

    class ErrorAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, *args, **kwargs):
            raise httpx.RequestError("connection failed", request=request)

    with patch("httpx.AsyncClient", lambda *args, **kwargs: ErrorAsyncClient()):
        with pytest.raises(WeatherClientError):
            await get_current_weather("Saint Petersburg")

def test_format_weather_message_html_tags():
    data = {
        "main": {
            "temp": 12.34,
            "feels_like": 10.1,
            "humidity": 55,
        },
        "weather": [{"description": "пасмурно"}],
        "wind": {"speed": 3.2},
    }

    result = weather_client.format_weather_message("Москва", data)

    assert "<b>Москва</b>" in result
    assert "Температура: <b>12.3°C</b>" in result
    assert "Ощущается как: <b>10.1°C</b>" in result
    assert "Влажность: 55%" in result
    assert "Ветер: 3.2 м/с" in result
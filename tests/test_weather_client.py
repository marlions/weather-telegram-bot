from app.weather_client import get_current_weather, WeatherClientError
from unittest.mock import patch
import pytest
from httpx import HTTPStatusError, Response

@pytest.mark.asyncio
async def test_valid_city():
    with patch('weather_client.get_current_weather', return_value={
        'weather': [{'description': 'clear sky'}],
        'main': {'temp': 20.0},
        'name': 'Saint Petersburg'
    }):
        city = "Saint Petersburg"
        response = await get_current_weather(city)
        assert response['weather'][0]['description'] == 'clear sky'
        assert response['main']['temp'] == 20.0
        assert response['name'] == 'Saint Petersburg'

@pytest.mark.asyncio
async def test_invalid_city():
    with patch('app.weather_client.get_current_weather', side_effect=WeatherClientError("City not found")):
        city = "InvalidCity"
        with pytest.raises(WeatherClientError):
            await get_current_weather(city)

@pytest.mark.asyncio
async def test_weather_api_error():
    with patch('app.weather_client.get_current_weather', side_effect=HTTPStatusError(
            "Not Found", request=None, response=Response(status_code=404))):
        city = "Saint Petersburg"
        with pytest.raises(HTTPStatusError):
            await get_current_weather(city)
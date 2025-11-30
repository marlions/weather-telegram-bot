from app.weather_client import get_current_weather, WeatherClientError
from unittest.mock import patch
import pytest
from aiohttp import ClientResponseError

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
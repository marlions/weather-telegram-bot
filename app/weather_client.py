from typing import Any, Dict
import httpx
from .config import settings

class WeatherClientError(Exception):
    pass
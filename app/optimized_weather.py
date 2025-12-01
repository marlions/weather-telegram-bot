import os
from .http_client import HTTPClient
from .cache import get_cached, set_cached

OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_KEY = os.getenv("OWM_KEY")
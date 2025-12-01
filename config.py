import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
OPEN_WEATHER_KEY = os.getenv("OPEN_WEATHER_KEY")
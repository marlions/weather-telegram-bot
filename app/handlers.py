"""
Телеграм-хендлеры.

Здесь будут функции для команд:
- /set_city
- /subscribe_daily
- /unsubscribe
- /current
и вспомогательная логика работы с состояниями.
"""

from aiogram import Router

router = Router()
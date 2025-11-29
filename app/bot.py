from aiogram import Dispatcher

from .handlers import router as handlers_router


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(handlers_router)
    return dp

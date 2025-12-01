import asyncio
from typing import Optional
import aiohttp

class HTTPClient:
    _session: Optional[aiohttp.ClientSession] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            async with cls._lock:
                if cls._session is None or cls._session.closed:
                    connector = aiohttp.TCPConnector(limit=100, force_close=False)
                    cls._session = aiohttp.ClientSession(connector=connector)
        return cls._session

    @classmethod
    async def fetch_json(cls, url: str, params: dict = None, timeout: int = 10):
        session = await cls.get_session()
        try:
            async with session.get(url, params=params, timeout=timeout) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception:
            # пробрасываем — вызывающий код решит как обрабатывать
            raise
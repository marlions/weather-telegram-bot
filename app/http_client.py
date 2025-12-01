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


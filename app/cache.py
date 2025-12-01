import os
import json
import asyncio
from typing import Any

REDIS_URL = os.getenv("REDIS_URL")

class InMemoryTTLCache:
    def __init__(self):
        self._store = {}  # key -> (ts, ttl, value)
        self._lock = asyncio.Lock()

    async def get(self, key: str):
        async with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            ts, ttl, value = item
            import time
            if time.time() - ts > ttl:
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: int = 300):
        async with self._lock:
            import time
            self._store[key] = (time.time(), ttl, value)

_inmem = InMemoryTTLCache()

_redis_client = None
try:
    if REDIS_URL:
        import aioredis

        async def _get_redis():
            global _redis_client
            if _redis_client is None:
                _redis_client = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
            return _redis_client

        async def get_cached(key: str):
            r = await _get_redis()
            if r is None:
                return await _inmem.get(key)
            data = await r.get(key)
            return json.loads(data) if data else None

        async def set_cached(key: str, value: Any, ttl: int = 300):
            r = await _get_redis()
            if r:
                await r.set(key, json.dumps(value), ex=ttl)
            else:
                await _inmem.set(key, value, ttl)
    else:
        async def get_cached(key: str):
            return await _inmem.get(key)

        async def set_cached(key: str, value: Any, ttl: int = 300):
            await _inmem.set(key, value, ttl)
except Exception:
    async def get_cached(key: str):
        return await _inmem.get(key)

    async def set_cached(key: str, value: Any, ttl: int = 300):
        await _inmem.set(key, value, ttl)
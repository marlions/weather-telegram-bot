import asyncio
import logging
import os
from typing import Optional, Any, Dict

import aiohttp
from aiohttp import ClientError, ClientResponse

logger = logging.getLogger(__name__)

_MAX_RETRIES = int(os.getenv("HTTPCLIENT_MAX_RETRIES", "3"))
_BACKOFF_INITIAL = float(os.getenv("HTTPCLIENT_BACKOFF_INITIAL", "0.5"))  # секунды
_BACKOFF_FACTOR = float(os.getenv("HTTPCLIENT_BACKOFF_FACTOR", "2.0"))
_TIMEOUT = float(os.getenv("HTTPCLIENT_TIMEOUT", "10"))  # seconds
_TCP_LIMIT = int(os.getenv("HTTPCLIENT_TCP_LIMIT", "100"))

class HTTPClient:
    _session: Optional[aiohttp.ClientSession] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            async with cls._lock:
                if cls._session is None or cls._session.closed:
                    connector = aiohttp.TCPConnector(limit=_TCP_LIMIT, force_close=False)
                    timeout = aiohttp.ClientTimeout(total=None)  # per-request timeout used below
                    cls._session = aiohttp.ClientSession(connector=connector, timeout=timeout)
                    logger.debug("HTTPClient: created new aiohttp ClientSession")
        return cls._session

    @classmethod
    async def _request_with_retries(cls, method: str, url: str, *, params: Dict[str, Any] = None,
                                    headers: Dict[str, str] = None, timeout: Optional[float] = None,
                                    max_retries: int = _MAX_RETRIES) -> ClientResponse:

        attempt = 0
        backoff = _BACKOFF_INITIAL
        last_exc = None
        sess = await cls.get_session()

        while attempt <= max_retries:
            try:
                req_timeout = timeout if timeout is not None else _TIMEOUT
                async with sess.request(method, url, params=params, headers=headers, timeout=req_timeout) as resp:
                    if 500 <= resp.status < 600:
                        text = await resp.text()
                        logger.warning("HTTPClient request got %s (attempt %s) for %s; response: %s",
                                       resp.status, attempt + 1, url, (text[:200] + "..." if len(text) > 200 else text))
                        last_exc = aiohttp.ClientResponseError(
                            request_info=resp.request_info,
                            history=resp.history,
                            status=resp.status,
                            message=f"Server error {resp.status}",
                            headers=resp.headers,
                        )
                        raise last_exc
                    return resp
            except (asyncio.TimeoutError, ClientError) as exc:
                last_exc = exc
                attempt += 1
                if attempt > max_retries:
                    logger.error("HTTPClient exhausted retries (%s) for url=%s; last_exc=%s", max_retries, url, repr(exc))
                    raise
                else:
                    jitter = backoff * 0.1
                    sleep_for = backoff + (jitter * (0.5 - os.urandom(1)[0] / 255.0))
                    logger.info("HTTPClient retry %s/%s for %s after %.2fs (error=%s)", attempt, max_retries, url, sleep_for, repr(exc))
                    await asyncio.sleep(max(0.0, sleep_for))
                    backoff *= _BACKOFF_FACTOR
            except Exception as exc:
                logger.exception("HTTPClient unexpected error for url=%s: %s", url, exc)
                raise
        if last_exc:
            raise last_exc
        raise RuntimeError("HTTPClient._request_with_retries failed unexpectedly")

    @classmethod
    async def fetch_json(cls, url: str, params: Dict[str, Any] = None, headers: Dict[str, str] = None,
                         timeout: Optional[float] = None, max_retries: int = _MAX_RETRIES) -> Any:
        resp = None
        try:
            resp = await cls._request_with_retries("GET", url, params=params, headers=headers, timeout=timeout, max_retries=max_retries)
            data = await resp.json()
            return data
        finally:
            pass

    @classmethod
    async def close(cls):
        if cls._session and not cls._session.closed:
            await cls._session.close()
            logger.debug("HTTPClient: ClientSession closed")
            cls._session = None
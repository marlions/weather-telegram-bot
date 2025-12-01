import os, asyncio
from app.http_client import HTTPClient
from app.cache import get_cached

async def main():
    ok = True
    try:
        await HTTPClient.get_session()
    except Exception:
        ok = False
    try:
        await get_cached("health:test")
    except Exception:
        ok = False
    print("OK" if ok else "NOT OK")

if __name__ == "__main__":
    asyncio.run(main())
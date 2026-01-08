import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта (/app), чтобы import app.* работал при запуске как файла:
# python tools/create_tables.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import engine
from app.models import Base


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("tables created")


if __name__ == "__main__":
    asyncio.run(main())

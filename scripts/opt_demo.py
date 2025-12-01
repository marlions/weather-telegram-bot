import asyncio
from app.optimized_weather import get_weather

async def main():
    cities = ["London", "Moscow", "New York", "Moscow", "London"]
    results = await asyncio.gather(*(get_weather(c, ttl=300) for c in cities))
    for c, r in zip(cities, results):
        descr = r.get("weather", [{}])[0].get("description", "<no>")
        print(f"{c}: {descr}")

if __name__ == "__main__":
    asyncio.run(main())
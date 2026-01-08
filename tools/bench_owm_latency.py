import os
import time
import statistics
import httpx

API = "https://api.openweathermap.org/data/2.5/weather"


def main():
    key = (
        os.environ.get("OPENWEATHER_API_KEY")
        or os.environ.get("OPEN_WEATHER_KEY")
        or os.environ.get("OWM_KEY")
    )
    if not key:
        raise SystemExit("Не задан ключ: OPENWEATHER_API_KEY (или OPEN_WEATHER_KEY / OWM_KEY)")

    city = os.environ.get("BENCH_CITY", "London")
    n = int(os.environ.get("BENCH_N", "30"))
    sleep_s = float(os.environ.get("BENCH_SLEEP", "1"))
    retries = int(os.environ.get("BENCH_RETRIES", "2"))

    timeout = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)

    times = []
    fails = 0

    with httpx.Client(timeout=timeout) as client:
        for i in range(1, n + 1):
            ok = False
            last_err = None

            for attempt in range(1, retries + 2):
                try:
                    t0 = time.perf_counter()
                    r = client.get(API, params={"q": city, "appid": key, "units": "metric", "lang": "ru"})
                    r.raise_for_status()
                    dt = (time.perf_counter() - t0) * 1000
                    times.append(dt)
                    ok = True
                    break
                except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                    last_err = type(e).__name__
                    time.sleep(0.5 * attempt)
                except httpx.HTTPStatusError as e:
                    raise SystemExit(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
                except Exception as e:
                    last_err = repr(e)
                    time.sleep(0.5 * attempt)

            print(f"[{i}/{n}] {'OK' if ok else 'FAIL: ' + str(last_err)}")
            if not ok:
                fails += 1

            time.sleep(sleep_s)

    if len(times) < max(5, n // 3):
        raise SystemExit(f"Слишком мало успешных измерений: ok={len(times)}, fails={fails}")

    times.sort()
    p50 = statistics.median(times)
    p95 = times[int(0.95 * len(times)) - 1]

    print()
    print(f"City={city}, requested={n}, ok={len(times)}, fails={fails}")
    print(
        "OpenWeather latency (ms):",
        f"p50={p50:.1f}",
        f"p95={p95:.1f}",
        f"min={min(times):.1f}",
        f"max={max(times):.1f}",
    )


if __name__ == "__main__":
    main()

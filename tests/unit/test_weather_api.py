import importlib
import pytest

@pytest.mark.asyncio
async def test_get_weather_fetches_and_caches(monkeypatch):
    monkeypatch.setenv("OPEN_WEATHER_KEY", "dummy_key_for_tests")
    import services.weather_api as wa
    importlib.reload(wa)

    fake_data = {
        "name": "TestCity",
        "main": {"temp": 12.0, "humidity": 80},
        "wind": {"speed": 3.0},
        "weather": [{"description": "sunny"}],
    }

    class FakeHTTPClient:
        @staticmethod
        async def fetch_json(url, params=None, timeout=10):
            return fake_data

    monkeypatch.setattr(wa, "HTTPClient", FakeHTTPClient)

    async def fake_get_cached(key):
        return None

    called = {}

    async def fake_set_cached(key, value, ttl=300):
        called["key"] = key
        called["value"] = value

    monkeypatch.setattr(wa, "get_cached", fake_get_cached)
    monkeypatch.setattr(wa, "set_cached", fake_set_cached)

    res = await wa.get_weather("TestCity")

    assert res is not None
    assert res["city"] == "TestCity"
    assert res["temp"] == 12.0
    assert res["humidity"] == 80
    assert res["wind"] == 3.0
    assert res["description"] == "sunny"
    assert called.get("key") == "weather:testcity:metric"
    assert called.get("value") == res


@pytest.mark.asyncio
async def test_get_weather_returns_cached(monkeypatch):
    monkeypatch.setenv("OPEN_WEATHER_KEY", "dummy_key_for_tests")
    import services.weather_api as wa
    importlib.reload(wa)

    fake_cached = {
        "city": "CachedCity",
        "temp": 10.0,
        "humidity": 50,
        "wind": 2.0,
        "description": "cached",
    }

    async def fake_get_cached(key):
        return fake_cached

    async def should_not_fetch(url, params=None, timeout=10):
        raise AssertionError("HTTP fetch should not be called when cache returns value")

    monkeypatch.setattr(wa, "get_cached", fake_get_cached)
    monkeypatch.setattr(wa, "_fetch_json_direct", should_not_fetch)
    monkeypatch.setattr(wa, "HTTPClient", None)

    res = await wa.get_weather("AnyCityName")
    assert res == fake_cached
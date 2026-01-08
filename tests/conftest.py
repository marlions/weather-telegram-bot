import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", os.getenv("BOT_TOKEN", "test-token"))
    monkeypatch.setenv("OPENWEATHER_API_KEY", os.getenv("OPENWEATHER_API_KEY", "test-key"))
    monkeypatch.setenv("OPEN_WEATHER_KEY", os.getenv("OPEN_WEATHER_KEY", "test-key"))
    monkeypatch.setenv("OWM_KEY", os.getenv("OWM_KEY", "test-key"))

@pytest.fixture(autouse=True)
def _block_network(monkeypatch, request):
    if request.node.get_closest_marker("integration") or request.node.get_closest_marker("network"):
        return

    import httpx

    def _boom(*args, **kwargs):
        raise RuntimeError(
            "Network is blocked in unit tests. "
            "Mock httpx/aiohttp or mark the test with @pytest.mark.network"
        )

    monkeypatch.setattr(httpx.Client, "request", _boom, raising=True)
    monkeypatch.setattr(httpx.AsyncClient, "request", _boom, raising=True)

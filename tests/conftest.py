import pytest
import fakeredis.aioredis as fakeredis
import respx
from fastapi.testclient import TestClient

from app.main import app
from app.services import token_store


VALID_KEY = "coordinator_secret_key_min_32_chars_long"


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    monkeypatch.setenv("COORDINATOR_INTERNAL_API_KEY", VALID_KEY)
    monkeypatch.setenv("BREVO_API_KEY", "test-brevo-key")
    monkeypatch.setenv("BREVO_SENDER_EMAIL", "noreply@hrmony.com")
    monkeypatch.setenv("WEBHOOK_BASE_URL", "http://localhost:8001")
    monkeypatch.setenv("HRMONY_BACKEND_URL", "http://localhost:3001")
    from app import config
    config.settings.coordinator_internal_api_key = VALID_KEY
    config.settings.brevo_api_key = "test-brevo-key"
    config.settings.webhook_base_url = "http://localhost:8001"
    config.settings.hrmony_backend_url = "http://localhost:3001"


@pytest.fixture
async def fake_redis():
    r = fakeredis.FakeRedis(decode_responses=True)
    token_store.set_redis(r)
    yield r
    await r.aclose()


@pytest.fixture
def client(fake_redis):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_http():
    with respx.mock(assert_all_called=False) as m:
        yield m

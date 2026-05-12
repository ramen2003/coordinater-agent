import asyncio
import json
import pytest
import respx
import httpx

from app.models import TriggerPayload
from app.services import token_store

PAYLOAD = TriggerPayload(
    application_id=1,
    job_id=10,
    job_title="Backend Engineer",
    job_description="Write code",
    candidate_name="Alice",
    candidate_email="alice@example.com",
    interviewer_user_id=5,
    interviewer_calendar_provider="google",
    interviewer_access_token="tok_abc",
    interviewer_refresh_token=None,
)


@pytest.fixture
def mock_external(mock_http):
    mock_http.post("https://www.googleapis.com/calendar/v3/calendars/primary/events").mock(
        return_value=httpx.Response(200, json={"id": "evt_1"})
    )
    mock_http.post("https://api.brevo.com/v3/smtp/email").mock(
        return_value=httpx.Response(201, json={"messageId": "msg_1"})
    )
    mock_http.patch(respx.pattern.M(url__regex=r".*internal/applications/1/status.*")).mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    return mock_http


@pytest.mark.asyncio
async def test_valid_token_confirms_and_calls_backend(fake_redis, client):
    slots = await token_store.create_slot_tokens(1, [{"slot_iso": "2026-05-20T10:00:00+00:00", "slot_label": "Tuesday 20 May, 10:00 AM UTC"}], PAYLOAD)
    token = slots[0].token

    with respx.mock(assert_all_called=False) as m:
        m.post("https://www.googleapis.com/calendar/v3/calendars/primary/events").mock(
            return_value=httpx.Response(200, json={"id": "evt_1"})
        )
        m.post("https://api.brevo.com/v3/smtp/email").mock(
            return_value=httpx.Response(201, json={"messageId": "msg_1"})
        )
        m.patch(url__regex=r"http://localhost:3001/internal/applications/1/status").mock(
            return_value=httpx.Response(200, json={"success": True})
        )

        resp = client.get(f"/confirm?token={token}")

    assert resp.status_code == 200
    assert "confirmed" in resp.text.lower()


@pytest.mark.asyncio
async def test_missing_token_returns_invalid_page(client, fake_redis):
    resp = client.get("/confirm?token=nonexistent-token-uuid")
    assert resp.status_code == 200
    assert "invalid" in resp.text.lower()


@pytest.mark.asyncio
async def test_already_used_token_returns_already_confirmed(fake_redis, client):
    slots = await token_store.create_slot_tokens(1, [{"slot_iso": "2026-05-20T10:00:00+00:00", "slot_label": "Tuesday 20 May, 10:00 AM UTC"}], PAYLOAD)
    token = slots[0].token

    with respx.mock(assert_all_called=False):
        client.get(f"/confirm?token={token}")

    resp = client.get(f"/confirm?token={token}")
    assert resp.status_code == 200
    assert "already" in resp.text.lower()


@pytest.mark.asyncio
async def test_race_condition_only_first_succeeds(fake_redis):
    slots = await token_store.create_slot_tokens(1, [{"slot_iso": "2026-05-20T10:00:00+00:00", "slot_label": "Tuesday 20 May, 10:00 AM UTC"}], PAYLOAD)
    token = slots[0].token

    results = await asyncio.gather(
        token_store.validate_and_consume_token(token),
        token_store.validate_and_consume_token(token),
        return_exceptions=True,
    )

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], token_store.TokenAlreadyUsedError)

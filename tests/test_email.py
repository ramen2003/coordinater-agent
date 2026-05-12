import json

import httpx
import pytest
import respx

from app.models import SlotToken, TriggerPayload
from app.services import email

NESTJS_EMAIL_URL = "http://localhost:3001/internal/email/send"
VALID_KEY = "coordinator_secret_key_min_32_chars_long"

SLOT_TOKENS = [
    SlotToken(token="uuid-1111", slot_iso="2026-05-20T10:00:00+00:00", slot_label="Wednesday 20 May, 10:00 AM UTC"),
    SlotToken(token="uuid-2222", slot_iso="2026-05-20T11:00:00+00:00", slot_label="Wednesday 20 May, 11:00 AM UTC"),
]

PAYLOAD = TriggerPayload(
    application_id=1,
    job_id=10,
    job_title="Backend Engineer",
    job_description="Write code",
    candidate_name="Alice",
    candidate_email="alice@example.com",
    interviewer_user_id=5,
    interviewer_email="interviewer@example.com",
    interviewer_calendar_provider="google",
    interviewer_access_token="tok_abc",
)


@pytest.fixture
def nestjs_mock(mock_http):
    mock_http.post(NESTJS_EMAIL_URL).mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    return mock_http


@pytest.mark.asyncio
async def test_slot_selection_uses_correct_template(nestjs_mock):
    await email.send_slot_selection_email(
        candidate_name="Alice",
        candidate_email="alice@example.com",
        job_title="Backend Engineer",
        slot_tokens=SLOT_TOKENS,
    )
    body = json.loads(nestjs_mock.calls[0].request.content)
    assert body["template"] == "slot-selection"
    assert body["to"] == "alice@example.com"
    assert "Backend Engineer" in body["subject"]
    assert "candidateName" in body["variables"]
    assert "slots" in body["variables"]


@pytest.mark.asyncio
async def test_slot_selection_internal_api_key_present(nestjs_mock):
    await email.send_slot_selection_email(
        candidate_name="Alice",
        candidate_email="alice@example.com",
        job_title="Backend Engineer",
        slot_tokens=SLOT_TOKENS,
    )
    headers = nestjs_mock.calls[0].request.headers
    assert headers["x-internal-api-key"] == VALID_KEY


@pytest.mark.asyncio
async def test_confirm_links_contain_correct_tokens(nestjs_mock):
    await email.send_slot_selection_email(
        candidate_name="Bob",
        candidate_email="bob@example.com",
        job_title="Frontend Engineer",
        slot_tokens=SLOT_TOKENS,
    )
    body = json.loads(nestjs_mock.calls[0].request.content)
    confirm_urls = [s["confirmUrl"] for s in body["variables"]["slots"]]
    assert any("uuid-1111" in url for url in confirm_urls)
    assert any("uuid-2222" in url for url in confirm_urls)


@pytest.mark.asyncio
async def test_confirmation_emails_send_twice(nestjs_mock):
    await email.send_confirmation_emails(
        candidate_email="alice@example.com",
        candidate_name="Alice",
        interviewer_email="interviewer@example.com",
        job_title="Backend Engineer",
        slot_iso="2026-05-20T10:00:00+00:00",
    )
    assert len(nestjs_mock.calls) == 2
    recipients = [
        json.loads(call.request.content)["to"]
        for call in nestjs_mock.calls
    ]
    assert "alice@example.com" in recipients
    assert "interviewer@example.com" in recipients


@pytest.mark.asyncio
async def test_confirmation_emails_use_correct_template(nestjs_mock):
    await email.send_confirmation_emails(
        candidate_email="alice@example.com",
        candidate_name="Alice",
        interviewer_email="interviewer@example.com",
        job_title="Backend Engineer",
        slot_iso="2026-05-20T10:00:00+00:00",
    )
    for call in nestjs_mock.calls:
        body = json.loads(call.request.content)
        assert body["template"] == "interview-confirmed"
        assert "recipientName" in body["variables"]
        assert "interviewDateTime" in body["variables"]


@pytest.mark.asyncio
async def test_no_slots_uses_correct_template_and_recipient(nestjs_mock):
    await email.send_no_slots_notification(PAYLOAD)
    body = json.loads(nestjs_mock.calls[0].request.content)
    assert body["template"] == "no-slots"
    assert body["to"] == "interviewer@example.com"
    assert "No Available Slots" in body["subject"]
    assert body["variables"]["jobTitle"] == "Backend Engineer"
    assert nestjs_mock.calls[0].request.headers["x-internal-api-key"] == VALID_KEY


@pytest.mark.asyncio
async def test_reconnect_uses_correct_template_and_recipient(nestjs_mock):
    await email.send_recruiter_reconnect_notice(PAYLOAD)
    body = json.loads(nestjs_mock.calls[0].request.content)
    assert body["template"] == "reconnect-calendar"
    assert body["to"] == "interviewer@example.com"
    assert body["variables"]["candidateName"] == "Alice"
    assert nestjs_mock.calls[0].request.headers["x-internal-api-key"] == VALID_KEY

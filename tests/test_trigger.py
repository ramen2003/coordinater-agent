import pytest

VALID_KEY = "coordinator_secret_key_min_32_chars_long"

VALID_PAYLOAD = {
    "application_id": 1,
    "job_id": 10,
    "job_title": "Backend Engineer",
    "job_description": "Write code",
    "candidate_name": "Alice",
    "candidate_email": "alice@example.com",
    "interviewer_user_id": 5,
    "interviewer_calendar_provider": "google",
    "interviewer_access_token": "tok_abc",
    "interviewer_refresh_token": None,
}


def test_trigger_valid_key_returns_202(client):
    resp = client.post(
        "/trigger",
        json=VALID_PAYLOAD,
        headers={"x-internal-api-key": VALID_KEY},
    )
    assert resp.status_code == 202


def test_trigger_wrong_key_returns_401(client):
    resp = client.post(
        "/trigger",
        json=VALID_PAYLOAD,
        headers={"x-internal-api-key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_trigger_missing_fields_returns_422(client):
    resp = client.post(
        "/trigger",
        json={"application_id": 1},
        headers={"x-internal-api-key": VALID_KEY},
    )
    assert resp.status_code == 422

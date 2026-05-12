from datetime import datetime, timedelta, timezone

import httpx

TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0)


async def create_calendar_event(
    interviewer_access_token: str,
    interviewer_email: str,
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    slot_iso: str,
) -> dict:
    slot_start = datetime.fromisoformat(slot_iso.replace("Z", "+00:00"))
    slot_end = slot_start + timedelta(hours=1)

    event = {
        "summary": f"Interview: {job_title} — {candidate_name}",
        "start": {"dateTime": slot_start.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": slot_end.isoformat(), "timeZone": "UTC"},
        "attendees": [
            {"email": interviewer_email},
            {"email": candidate_email},
        ],
        "sendUpdates": "all",
    }

    async with httpx.AsyncClient(timeout=TIMEOUT, verify=True) as client:
        resp = await client.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            params={"sendUpdates": "all"},
            headers={"Authorization": f"Bearer {interviewer_access_token}"},
            json=event,
        )

    resp.raise_for_status()
    return resp.json()

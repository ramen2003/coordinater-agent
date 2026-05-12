from datetime import datetime, timezone

import httpx
import pytest
import respx

from app.services.calendar import CalendarTokenExpiredError, get_free_slots

BUSY_RESPONSE = {
    "calendars": {
        "primary": {
            "busy": [
                {
                    "start": "2026-05-12T09:00:00+00:00",
                    "end": "2026-05-12T11:00:00+00:00",
                },
            ]
        }
    }
}

EMPTY_RESPONSE = {
    "calendars": {"primary": {"busy": []}}
}


@pytest.mark.asyncio
async def test_busy_blocks_excluded_from_slots():
    with respx.mock() as m:
        m.post("https://www.googleapis.com/calendar/v3/freeBusy").mock(
            return_value=httpx.Response(200, json=BUSY_RESPONSE)
        )
        slots = await get_free_slots("tok_test", days_ahead=7)

    slot_isos = [s["slot_iso"] for s in slots]
    # The busy block covers 09:00–11:00 on the first working day, so those hours should be absent
    for iso in slot_isos:
        dt = datetime.fromisoformat(iso)
        if dt.hour in (9, 10) and dt.weekday() < 5:
            # Only flag if it's on the exact busy day (12 May)
            assert dt.day != 12 or dt.month != 5, f"Busy slot {iso} should not appear"


@pytest.mark.asyncio
async def test_empty_calendar_returns_multiple_slots():
    with respx.mock() as m:
        m.post("https://www.googleapis.com/calendar/v3/freeBusy").mock(
            return_value=httpx.Response(200, json=EMPTY_RESPONSE)
        )
        slots = await get_free_slots("tok_test", days_ahead=7)

    assert len(slots) > 1
    assert len(slots) <= 5


@pytest.mark.asyncio
async def test_401_raises_calendar_token_expired():
    with respx.mock() as m:
        m.post("https://www.googleapis.com/calendar/v3/freeBusy").mock(
            return_value=httpx.Response(401, json={"error": "unauthorized"})
        )
        with pytest.raises(CalendarTokenExpiredError):
            await get_free_slots("expired_tok", days_ahead=7)


@pytest.mark.asyncio
async def test_slots_are_weekdays_only():
    with respx.mock() as m:
        m.post("https://www.googleapis.com/calendar/v3/freeBusy").mock(
            return_value=httpx.Response(200, json=EMPTY_RESPONSE)
        )
        slots = await get_free_slots("tok_test", days_ahead=14)

    for slot in slots:
        dt = datetime.fromisoformat(slot["slot_iso"])
        assert dt.weekday() < 5, f"Slot {slot['slot_iso']} falls on a weekend"
        assert 9 <= dt.hour < 18, f"Slot {slot['slot_iso']} outside work hours"

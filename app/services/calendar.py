from datetime import datetime, timedelta, timezone, time

import httpx

TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0)
SLOT_DURATION = timedelta(hours=1)
WORK_START = time(9, 0)
WORK_END = time(18, 0)
MAX_SLOTS = 5
PKT = timezone(timedelta(hours=5))


class CalendarTokenExpiredError(Exception):
    pass


def _working_days_ahead(days_ahead: int) -> list[datetime]:
    now = datetime.now(timezone.utc)
    result: list[datetime] = []
    candidate = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    while len(result) < days_ahead:
        if candidate.weekday() < 5:
            result.append(candidate)
        candidate += timedelta(days=1)
    return result


def _free_slots_for_day(
    day: datetime,
    busy_intervals: list[tuple[datetime, datetime]],
) -> list[datetime]:
    work_start = day.replace(hour=WORK_START.hour, minute=WORK_START.minute)
    work_end = day.replace(hour=WORK_END.hour, minute=WORK_END.minute)
    slots: list[datetime] = []
    cursor = work_start

    while cursor + SLOT_DURATION <= work_end:
        slot_end = cursor + SLOT_DURATION
        overlaps = any(
            not (slot_end <= b_start or cursor >= b_end)
            for b_start, b_end in busy_intervals
        )
        if not overlaps:
            slots.append(cursor)
        cursor += SLOT_DURATION

    return slots


async def get_free_slots(
    access_token: str,
    days_ahead: int = 7,
    slot_duration_minutes: int = 60,
) -> list[dict[str, str]]:
    work_days = _working_days_ahead(days_ahead)
    time_min = work_days[0].isoformat()
    time_max = (work_days[-1] + timedelta(days=1)).isoformat()

    async with httpx.AsyncClient(timeout=TIMEOUT, verify=True) as client:
        resp = await client.post(
            "https://www.googleapis.com/calendar/v3/freeBusy",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": "primary"}],
            },
        )

    if resp.status_code == 401:
        raise CalendarTokenExpiredError("Google token expired or revoked")

    resp.raise_for_status()
    body = resp.json()

    busy_raw = body.get("calendars", {}).get("primary", {}).get("busy", [])
    busy_intervals: list[tuple[datetime, datetime]] = []
    for interval in busy_raw:
        b_start = datetime.fromisoformat(interval["start"].replace("Z", "+00:00"))
        b_end = datetime.fromisoformat(interval["end"].replace("Z", "+00:00"))
        busy_intervals.append((b_start, b_end))

    free: list[dict[str, str]] = []
    for day in work_days:
        if len(free) >= MAX_SLOTS:
            break
        day_slots = _free_slots_for_day(day, busy_intervals)
        for slot in day_slots:
            if len(free) >= MAX_SLOTS:
                break
            slot_pkt = slot.astimezone(PKT)
            label = slot_pkt.strftime("%A %-d %B, %I:%M %p PKT")
            free.append({"slot_iso": slot.isoformat(), "slot_label": label})

    return free

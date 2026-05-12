from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from app.services import backend, booking, email, token_store
from app.services.token_store import TokenAlreadyUsedError, TokenNotFoundError

PKT = timezone(timedelta(hours=5))


def _format_slot(slot_iso: str) -> str:
    dt = datetime.fromisoformat(slot_iso.replace("Z", "+00:00")).astimezone(PKT)
    return dt.strftime("%A %-d %B %Y, %I:%M %p PKT")

router = APIRouter()

_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{title}</title>
<style>body{{font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#f9fafb;}}
.card{{background:#fff;border-radius:12px;padding:48px 40px;box-shadow:0 4px 24px rgba(0,0,0,.08);max-width:480px;text-align:center;}}
h1{{color:{color};margin-bottom:12px;font-size:24px;}} p{{color:#555;line-height:1.6;}}</style>
</head><body><div class="card"><h1>{title}</h1><p>{body}</p></div></body></html>"""


def _html(title: str, body: str, color: str = "#1a1a2e") -> HTMLResponse:
    return HTMLResponse(_HTML.format(title=title, body=body, color=color))


@router.get("/confirm", response_class=HTMLResponse)
async def confirm(token: str = Query(...)):
    try:
        data = await token_store.validate_and_consume_token(token)
    except TokenNotFoundError:
        return _html("Link Invalid", "This link is invalid.", color="#dc2626")
    except TokenAlreadyUsedError:
        return _html(
            "Already Confirmed",
            "You&#39;ve already confirmed a slot. Check your email for the calendar invite.",
            color="#d97706",
        )

    payload_data = data["payload"]
    slot_iso = data["slot_iso"]
    application_id = data["application_id"]

    interviewer_email = payload_data["interviewer_email"]

    try:
        await booking.create_calendar_event(
            interviewer_access_token=payload_data["interviewer_access_token"],
            interviewer_email=interviewer_email,
            candidate_email=payload_data["candidate_email"],
            candidate_name=payload_data["candidate_name"],
            job_title=payload_data["job_title"],
            slot_iso=slot_iso,
        )
    except Exception:
        pass

    try:
        await email.send_confirmation_emails(
            candidate_email=payload_data["candidate_email"],
            candidate_name=payload_data["candidate_name"],
            interviewer_email=interviewer_email,
            job_title=payload_data["job_title"],
            slot_iso=_format_slot(slot_iso),
        )
    except Exception:
        pass

    try:
        await backend.update_application_status(
            application_id=application_id,
            status="confirmed_interview",
            interview_at=slot_iso,
        )
    except Exception:
        pass

    return _html(
        "Interview Confirmed!",
        "Your interview is confirmed! Check your email for the calendar invite.",
        color="#16a34a",
    )

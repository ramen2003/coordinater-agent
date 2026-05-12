import httpx

from app.config import settings
from app.models import SlotToken, TriggerPayload

TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0)


def _email_url() -> str:
    return f"{settings.hrmony_backend_url}/internal/email/send"


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "x-internal-api-key": settings.coordinator_internal_api_key,
    }


async def _post_email(template: str, to: str, subject: str, variables: dict) -> None:
    async with httpx.AsyncClient(timeout=TIMEOUT, verify=True) as client:
        resp = await client.post(
            _email_url(),
            headers=_headers(),
            json={"template": template, "to": to, "subject": subject, "variables": variables},
        )
    resp.raise_for_status()


async def send_slot_selection_email(
    candidate_name: str,
    candidate_email: str,
    job_title: str,
    slot_tokens: list[SlotToken],
) -> None:
    slots = [
        {
            "label": t.slot_label,
            "confirmUrl": f"{settings.webhook_base_url}/confirm?token={t.token}",
        }
        for t in slot_tokens
    ]
    await _post_email(
        template="slot-selection",
        to=candidate_email,
        subject=f"Interview Slots Available — {job_title}",
        variables={
            "candidateName": candidate_name,
            "jobTitle": job_title,
            "slots": slots,
        },
    )


async def send_confirmation_emails(
    candidate_email: str,
    candidate_name: str,
    interviewer_email: str,
    job_title: str,
    slot_iso: str,
) -> None:
    for recipient_email, recipient_name in [
        (candidate_email, candidate_name),
        (interviewer_email, "Interviewer"),
    ]:
        await _post_email(
            template="interview-confirmed",
            to=recipient_email,
            subject=f"Interview Confirmed — {job_title}",
            variables={
                "recipientName": recipient_name,
                "jobTitle": job_title,
                "interviewDateTime": slot_iso,
            },
        )


async def send_no_slots_notification(payload: TriggerPayload) -> None:
    await _post_email(
        template="no-slots",
        to=payload.interviewer_email,
        subject=f"No Available Slots — {payload.job_title}",
        variables={
            "jobTitle": payload.job_title,
            "candidateName": payload.candidate_name,
        },
    )


async def send_recruiter_reconnect_notice(payload: TriggerPayload) -> None:
    await _post_email(
        template="reconnect-calendar",
        to=payload.interviewer_email,
        subject="Action Required: Reconnect Your Calendar",
        variables={
            "jobTitle": payload.job_title,
            "candidateName": payload.candidate_name,
        },
    )

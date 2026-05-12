import logging

from app.models import TriggerPayload
from app.services import calendar, email, token_store
from app.services.calendar import CalendarTokenExpiredError
from app.services.retry import with_retry

logger = logging.getLogger(__name__)


async def run_pipeline(payload: TriggerPayload) -> None:
    try:
        slots = await calendar.get_free_slots(
            access_token=payload.interviewer_access_token,
            days_ahead=7,
            slot_duration_minutes=60,
        )
        if not slots:
            await email.send_no_slots_notification(payload)
            return

        slot_tokens = await token_store.create_slot_tokens(
            application_id=payload.application_id,
            slots=slots,
            payload=payload,
        )

        await with_retry(
            lambda: email.send_slot_selection_email(
                candidate_name=payload.candidate_name,
                candidate_email=payload.candidate_email,
                job_title=payload.job_title,
                slot_tokens=slot_tokens,
            )
        )

    except CalendarTokenExpiredError:
        await email.send_recruiter_reconnect_notice(payload)
    except Exception as exc:
        logger.error("Pipeline failed for application %s: %s", payload.application_id, exc)

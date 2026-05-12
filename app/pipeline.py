import logging

from app.models import TriggerPayload
from app.services import backend, calendar, email, token_store
from app.services.calendar import CalendarTokenExpiredError, CalendarTokenRefreshError, refresh_google_token
from app.services.retry import with_retry

logger = logging.getLogger(__name__)


async def _get_free_slots_with_refresh(payload: TriggerPayload) -> tuple[list[dict], str]:
    """
    Fetch free slots, auto-refreshing the access token on 401.
    Returns (slots, access_token_used) so callers have the current token.
    Raises CalendarTokenExpiredError if refresh is impossible or fails.
    """
    try:
        slots = await calendar.get_free_slots(
            access_token=payload.interviewer_access_token,
            days_ahead=7,
            slot_duration_minutes=60,
        )
        return slots, payload.interviewer_access_token

    except CalendarTokenExpiredError:
        if not payload.interviewer_refresh_token:
            raise

        logger.info(
            "Access token expired for user %s — attempting refresh",
            payload.interviewer_user_id,
        )
        try:
            new_token = await refresh_google_token(payload.interviewer_refresh_token)
        except CalendarTokenRefreshError as exc:
            logger.warning("Token refresh failed for user %s: %s", payload.interviewer_user_id, exc)
            raise CalendarTokenExpiredError("Refresh token invalid or revoked") from exc

        # Persist the new token so future pipeline runs don't also fail.
        try:
            await backend.update_calendar_token(
                user_id=payload.interviewer_user_id,
                access_token=new_token["access_token"],
                expires_at=new_token.get("expires_at"),
            )
        except Exception as exc:
            logger.warning("Could not persist refreshed token for user %s: %s", payload.interviewer_user_id, exc)

        slots = await calendar.get_free_slots(
            access_token=new_token["access_token"],
            days_ahead=7,
            slot_duration_minutes=60,
        )
        return slots, new_token["access_token"]


async def run_pipeline(payload: TriggerPayload) -> None:
    try:
        slots, _ = await _get_free_slots_with_refresh(payload)

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
        logger.warning(
            "Calendar token expired/revoked for application %s — notifying %s",
            payload.application_id,
            payload.interviewer_email,
        )
        await email.send_recruiter_reconnect_notice(payload)
    except Exception as exc:
        logger.error("Pipeline failed for application %s: %s", payload.application_id, exc)

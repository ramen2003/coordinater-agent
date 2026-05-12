import httpx
from app.config import settings

TIMEOUT = httpx.Timeout(connect=10.0, read=10.0, write=10.0, pool=5.0)


async def update_application_status(
    application_id: int,
    status: str,
    interview_at: str,
) -> None:
    url = f"{settings.hrmony_backend_url}/internal/applications/{application_id}/status"
    async with httpx.AsyncClient(timeout=TIMEOUT, verify=True) as client:
        resp = await client.patch(
            url,
            headers={"x-internal-api-key": settings.coordinator_internal_api_key},
            json={"status": status, "interview_at": interview_at},
        )
    resp.raise_for_status()


async def update_calendar_token(
    user_id: int,
    access_token: str,
    expires_at: str | None,
) -> None:
    url = f"{settings.hrmony_backend_url}/internal/calendar-token"
    async with httpx.AsyncClient(timeout=TIMEOUT, verify=True) as client:
        resp = await client.patch(
            url,
            headers={"x-internal-api-key": settings.coordinator_internal_api_key},
            json={"user_id": user_id, "access_token": access_token, "expires_at": expires_at},
        )
    resp.raise_for_status()

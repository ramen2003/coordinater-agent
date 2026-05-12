from typing import Literal
from pydantic import BaseModel


class SlotToken(BaseModel):
    token: str
    slot_iso: str
    slot_label: str


class TriggerPayload(BaseModel):
    application_id: int
    job_id: int
    job_title: str
    job_description: str
    candidate_name: str
    candidate_email: str
    interviewer_user_id: int
    interviewer_email: str
    interviewer_calendar_provider: Literal["google"]
    interviewer_access_token: str
    interviewer_refresh_token: str | None = None

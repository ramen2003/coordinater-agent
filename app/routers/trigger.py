import asyncio

from fastapi import APIRouter, Depends, status

from app.dependencies import verify_internal_key
from app.models import TriggerPayload
from app.pipeline import run_pipeline

router = APIRouter()


@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_internal_key)])
async def trigger(payload: TriggerPayload):
    asyncio.create_task(run_pipeline(payload))
    return {"accepted": True}

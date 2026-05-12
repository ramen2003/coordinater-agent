import json
import uuid
from typing import Any

import redis.asyncio as aioredis

from app.config import settings
from app.models import SlotToken, TriggerPayload

_redis: aioredis.Redis | None = None

TOKEN_TTL = settings.token_ttl_hours * 3600


class TokenNotFoundError(Exception):
    pass


class TokenAlreadyUsedError(Exception):
    pass


def _key(token: str) -> str:
    return f"slot_token:{token}"


def set_redis(r: aioredis.Redis) -> None:
    global _redis
    _redis = r


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialised")
    return _redis


async def create_slot_tokens(
    application_id: int,
    slots: list[dict[str, str]],
    payload: TriggerPayload,
) -> list[SlotToken]:
    r = get_redis()
    result: list[SlotToken] = []

    for slot in slots:
        token = str(uuid.uuid4())
        data: dict[str, Any] = {
            "status": "pending",
            "application_id": application_id,
            "slot_iso": slot["slot_iso"],
            "slot_label": slot["slot_label"],
            "payload": payload.model_dump(),
        }
        await r.setex(_key(token), TOKEN_TTL, json.dumps(data))
        result.append(
            SlotToken(token=token, slot_iso=slot["slot_iso"], slot_label=slot["slot_label"])
        )

    return result


async def validate_and_consume_token(token: str) -> dict[str, Any]:
    r = get_redis()
    key = _key(token)

    raw = await r.get(key)
    if raw is None:
        raise TokenNotFoundError(token)

    data: dict[str, Any] = json.loads(raw)

    if data.get("status") != "pending":
        raise TokenAlreadyUsedError(token)

    data["status"] = "used"
    await r.set(key, json.dumps(data), keepttl=True)

    return data

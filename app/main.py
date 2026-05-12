import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI

from app.config import settings
from app.routers import confirm, trigger
from app.services import token_store

logging.basicConfig(level=settings.log_level.upper())


@asynccontextmanager
async def lifespan(app: FastAPI):
    r = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_timeout=10,
        socket_connect_timeout=10,
    )
    token_store.set_redis(r)
    yield
    await r.aclose()


app = FastAPI(title="Coordinator Agent", lifespan=lifespan)

app.include_router(trigger.router)
app.include_router(confirm.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

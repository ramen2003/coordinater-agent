import asyncio
import logging
from typing import Callable, Awaitable, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


async def with_retry(
    coro_fn: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    base_delay: float = 2.0,
) -> T:
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await coro_fn()
        except Exception as exc:
            last_exc = exc
            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning("Attempt %d/%d failed, retrying in %.1fs: %s", attempt, max_attempts, delay, exc)
                await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]

import time

import httpx

from app.checkers.base import CheckOutcome
from app.models import CheckStatus


async def check(config: dict) -> CheckOutcome:
    url: str = config["url"]
    timeout_seconds: float = float(config.get("timeout_seconds", 10))
    expect_status_below: int = int(config.get("expect_status_below", 500))

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds) as client:
            response = await client.get(url)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        is_up = response.status_code < expect_status_below
        return CheckOutcome(
            status=CheckStatus.UP if is_up else CheckStatus.DOWN,
            response_time_ms=elapsed_ms,
            detail={"status_code": response.status_code},
        )
    except httpx.HTTPError as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return CheckOutcome(
            status=CheckStatus.DOWN,
            response_time_ms=elapsed_ms,
            detail={"error": str(exc)},
        )

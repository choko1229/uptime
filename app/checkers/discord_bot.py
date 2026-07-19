import time

import httpx

from app.checkers.base import CheckOutcome
from app.models import CheckStatus

WIDGET_URL = "https://discord.com/api/guilds/{guild_id}/widget.json"


async def check(config: dict) -> CheckOutcome:
    guild_id: str = str(config["guild_id"])
    bot_username: str = config["bot_username"].lower()
    timeout_seconds: float = float(config.get("timeout_seconds", 10))

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(WIDGET_URL.format(guild_id=guild_id))
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if response.status_code == 404:
            return CheckOutcome(
                status=CheckStatus.DOWN,
                response_time_ms=elapsed_ms,
                detail={"error": "widget_disabled_or_guild_not_found"},
            )
        response.raise_for_status()
        data = response.json()
        members = data.get("members", [])
        match = next(
            (m for m in members if str(m.get("username", "")).lower() == bot_username),
            None,
        )
        is_up = match is not None and match.get("status") != "offline"
        detail = {
            "presence_count": data.get("presence_count"),
            "found": match is not None,
            "status": match.get("status") if match else None,
        }
        return CheckOutcome(
            status=CheckStatus.UP if is_up else CheckStatus.DOWN,
            response_time_ms=elapsed_ms,
            detail=detail,
        )
    except httpx.HTTPError as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return CheckOutcome(
            status=CheckStatus.DOWN,
            response_time_ms=elapsed_ms,
            detail={"error": str(exc)},
        )

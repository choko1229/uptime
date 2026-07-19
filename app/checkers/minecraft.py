import time

from mcstatus import BedrockServer, JavaServer

from app.checkers.base import CheckOutcome
from app.models import CheckStatus


async def check(config: dict) -> CheckOutcome:
    address: str = config["address"]
    edition: str = config.get("edition", "java")

    start = time.monotonic()
    try:
        if edition == "bedrock":
            server = BedrockServer.lookup(address)
            status = await server.async_status()
            elapsed_ms = int((time.monotonic() - start) * 1000)
            detail = {
                "players_online": status.players.online,
                "players_max": status.players.max,
                "motd": status.motd.raw if status.motd else None,
                "version": status.version.name,
            }
        else:
            server = JavaServer.lookup(address)
            status = await server.async_status()
            elapsed_ms = int((time.monotonic() - start) * 1000)
            detail = {
                "players_online": status.players.online,
                "players_max": status.players.max,
                "motd": status.motd.raw if status.motd else None,
                "version": status.version.name,
            }
        return CheckOutcome(
            status=CheckStatus.UP, response_time_ms=elapsed_ms, detail=detail
        )
    except Exception as exc:  # noqa: BLE001 - any failure to query means the server is down
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return CheckOutcome(
            status=CheckStatus.DOWN,
            response_time_ms=elapsed_ms,
            detail={"error": str(exc)},
        )

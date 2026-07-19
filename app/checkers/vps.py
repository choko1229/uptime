import asyncio
import platform
import time

from app.checkers.base import CheckOutcome
from app.models import CheckStatus


async def _ping(host: str, timeout_seconds: int = 3) -> bool:
    count_flag = "-n" if platform.system().lower() == "windows" else "-c"
    timeout_flag = "-w" if platform.system().lower() == "windows" else "-W"
    timeout_value = str(timeout_seconds * 1000) if platform.system().lower() == "windows" else str(timeout_seconds)
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping",
            count_flag,
            "1",
            timeout_flag,
            timeout_value,
            host,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        returncode = await asyncio.wait_for(proc.wait(), timeout=timeout_seconds + 2)
        return returncode == 0
    except (FileNotFoundError, asyncio.TimeoutError, OSError):
        return False


async def _tcp_connect(host: str, port: int, timeout_seconds: int = 3) -> bool:
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout_seconds
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (TimeoutError, OSError, asyncio.TimeoutError):
        return False


async def check(config: dict) -> CheckOutcome:
    host: str = config["host"]
    port: int = int(config.get("port", 22))
    ping_enabled: bool = config.get("ping_enabled", True)
    tcp_enabled: bool = config.get("tcp_enabled", True)

    start = time.monotonic()
    ping_ok = await _ping(host) if ping_enabled else False
    tcp_ok = await _tcp_connect(host, port) if tcp_enabled else False
    elapsed_ms = int((time.monotonic() - start) * 1000)

    is_up = ping_ok or tcp_ok
    return CheckOutcome(
        status=CheckStatus.UP if is_up else CheckStatus.DOWN,
        response_time_ms=elapsed_ms,
        detail={"ping_ok": ping_ok, "tcp_ok": tcp_ok, "port": port},
    )

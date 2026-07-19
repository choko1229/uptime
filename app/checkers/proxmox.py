import time

import httpx

from app.checkers.base import CheckOutcome
from app.models import CheckStatus


async def check(config: dict) -> CheckOutcome:
    host: str = config["host"]
    port: int = int(config.get("port", 8006))
    node: str = config["node"]
    vmid: int = int(config["vmid"])
    resource_type: str = config.get("resource_type", "qemu")  # qemu | lxc
    token_id: str = config["token_id"]  # e.g. "user@pam!tokenname"
    token_secret: str = config["token_secret"]
    verify_ssl: bool = config.get("verify_ssl", True)
    timeout_seconds: float = float(config.get("timeout_seconds", 10))

    url = f"https://{host}:{port}/api2/json/nodes/{node}/{resource_type}/{vmid}/status/current"
    headers = {"Authorization": f"PVEAPIToken={token_id}={token_secret}"}

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=timeout_seconds) as client:
            response = await client.get(url, headers=headers)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        response.raise_for_status()
        data = response.json().get("data", {})
        vm_status = data.get("status")  # "running" | "stopped" | ...
        is_up = vm_status == "running"

        cpu_fraction = data.get("cpu")
        mem = data.get("mem")
        maxmem = data.get("maxmem")
        disk = data.get("disk")
        maxdisk = data.get("maxdisk")

        detail = {
            "vm_status": vm_status,
            "cpu_percent": round(cpu_fraction * 100, 1) if cpu_fraction is not None else None,
            "mem_percent": round(mem / maxmem * 100, 1) if mem and maxmem else None,
            "mem_bytes": mem,
            "maxmem_bytes": maxmem,
            "disk_percent": round(disk / maxdisk * 100, 1) if disk and maxdisk else None,
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

from collections.abc import Awaitable, Callable

from app.checkers import discord_bot, minecraft, proxmox, vps, webpage
from app.checkers.base import CheckOutcome
from app.models import MonitorType

CHECKERS: dict[MonitorType, Callable[[dict], Awaitable[CheckOutcome]]] = {
    MonitorType.PROXMOX_VM: proxmox.check,
    MonitorType.VPS: vps.check,
    MonitorType.WEBPAGE: webpage.check,
    MonitorType.DISCORD_BOT: discord_bot.check,
    MonitorType.MINECRAFT: minecraft.check,
}


async def run_check(monitor_type: MonitorType, config: dict) -> CheckOutcome:
    return await CHECKERS[monitor_type](config)

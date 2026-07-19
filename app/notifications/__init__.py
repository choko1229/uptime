import logging

from app.notifications import discord, email
from app.models import NotificationChannel, NotificationType

logger = logging.getLogger(__name__)

_SENDERS = {
    NotificationType.DISCORD_WEBHOOK: discord.send,
    NotificationType.EMAIL: email.send,
}


async def notify(
    channel: NotificationChannel, *, title: str, description: str, status: str
) -> None:
    sender = _SENDERS[channel.type]
    try:
        await sender(channel.config, title=title, description=description, status=status)
    except Exception:
        logger.exception("Failed to send notification via channel %s (%s)", channel.id, channel.type)

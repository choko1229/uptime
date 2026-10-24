import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.app_settings import get_app_settings
from app.models import NotificationChannel, NotificationType
from app.notifications import discord, email

logger = logging.getLogger(__name__)

_SENDERS = {
    NotificationType.DISCORD_WEBHOOK: discord.send,
    NotificationType.EMAIL: email.send,
}


async def notify(
    db: AsyncSession,
    channel: NotificationChannel,
    *,
    title: str,
    description: str,
    status: str,
) -> None:
    sender = _SENDERS[channel.type]
    app_settings = await get_app_settings(db)
    try:
        await sender(
            channel.config,
            title=title,
            description=description,
            status=status,
            app_settings=app_settings,
        )
    except Exception:
        logger.exception(
            "Failed to send notification via channel %s (%s)", channel.id, channel.type
        )

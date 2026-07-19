from email.message import EmailMessage

import aiosmtplib

from app.config import get_settings


async def send(config: dict, *, title: str, description: str, status: str) -> None:
    settings = get_settings()
    to_address: str = config["to_address"]

    message = EmailMessage()
    message["From"] = settings.smtp_from_address or settings.smtp_username
    message["To"] = to_address
    message["Subject"] = title
    message.set_content(description)

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username or None,
        password=settings.smtp_password or None,
        start_tls=settings.smtp_use_tls,
    )

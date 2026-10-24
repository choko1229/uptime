from email.message import EmailMessage

import aiosmtplib

from app.models import AppSettings


async def send(
    config: dict, *, title: str, description: str, status: str, app_settings: AppSettings
) -> None:
    to_address: str = config["to_address"]

    if not app_settings.smtp_host:
        raise RuntimeError("SMTP is not configured yet (see /admin/settings)")

    message = EmailMessage()
    message["From"] = app_settings.smtp_from_address or app_settings.smtp_username
    message["To"] = to_address
    message["Subject"] = title
    message.set_content(description)

    await aiosmtplib.send(
        message,
        hostname=app_settings.smtp_host,
        port=app_settings.smtp_port,
        username=app_settings.smtp_username or None,
        password=app_settings.smtp_password or None,
        start_tls=app_settings.smtp_use_tls,
    )

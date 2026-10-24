from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppSettings

SETTINGS_ROW_ID = 1


async def get_app_settings(db: AsyncSession) -> AppSettings:
    settings = await db.get(AppSettings, SETTINGS_ROW_ID)
    if settings is None:
        settings = AppSettings(id=SETTINGS_ROW_ID)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


async def update_app_settings(db: AsyncSession, **fields) -> AppSettings:
    settings = await get_app_settings(db)
    for key, value in fields.items():
        setattr(settings, key, value)
    await db.commit()
    await db.refresh(settings)
    return settings

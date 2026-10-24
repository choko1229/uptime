from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.app_settings import get_app_settings
from app.db import get_db
from app.models import CheckResult, CheckStatus, Incident, Monitor
from app.uptime_calc import calculate_uptime_percent

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def status_page(request: Request, db: AsyncSession = Depends(get_db)):
    app_settings = await get_app_settings(db)
    result = await db.execute(
        select(Monitor)
        .where(Monitor.show_on_status_page.is_(True))
        .order_by(Monitor.sort_order, Monitor.id)
    )
    monitors = list(result.scalars())

    monitor_rows = []
    overall_up = True
    for monitor in monitors:
        latest = await db.scalar(
            select(CheckResult)
            .where(CheckResult.monitor_id == monitor.id)
            .order_by(CheckResult.checked_at.desc())
            .limit(1)
        )
        if monitor.last_status == CheckStatus.DOWN:
            overall_up = False
        uptime_30 = await calculate_uptime_percent(db, monitor.id, 30)
        uptime_90 = await calculate_uptime_percent(db, monitor.id, 90)
        monitor_rows.append(
            {
                "monitor": monitor,
                "latest": latest,
                "uptime_30": uptime_30,
                "uptime_90": uptime_90,
            }
        )

    ongoing_incidents = list(
        (
            await db.execute(
                select(Incident)
                .where(Incident.is_published.is_(True), Incident.status != "resolved")
                .order_by(Incident.started_at.desc())
            )
        ).scalars()
    )

    return templates.TemplateResponse(
        request,
        "public/status.html",
        {
            "site_title": app_settings.site_title,
            "monitor_rows": monitor_rows,
            "overall_up": overall_up,
            "ongoing_incidents": ongoing_incidents,
        },
    )


@router.get("/incidents")
async def incident_history(request: Request, db: AsyncSession = Depends(get_db)):
    app_settings = await get_app_settings(db)
    result = await db.execute(
        select(Incident)
        .options(selectinload(Incident.updates), selectinload(Incident.monitor))
        .where(Incident.is_published.is_(True))
        .order_by(Incident.started_at.desc())
    )
    incidents = list(result.scalars())
    return templates.TemplateResponse(
        request,
        "public/incidents.html",
        {"site_title": app_settings.site_title, "incidents": incidents},
    )

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.deps import require_admin
from app.models import (
    CheckResult,
    Incident,
    IncidentStatus,
    IncidentUpdate,
    Monitor,
    MonitorNotification,
    MonitorType,
    NotificationChannel,
    NotificationType,
)
from app.scheduler import schedule_monitor, unschedule_monitor

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory="app/templates")

MONITOR_TYPE_FIELDS: dict[MonitorType, list[str]] = {
    MonitorType.PROXMOX_VM: [
        "host",
        "port",
        "node",
        "vmid",
        "resource_type",
        "token_id",
        "token_secret",
        "verify_ssl",
    ],
    MonitorType.VPS: ["host", "port", "ping_enabled", "tcp_enabled"],
    MonitorType.WEBPAGE: ["url", "timeout_seconds", "expect_status_below"],
    MonitorType.DISCORD_BOT: ["guild_id", "bot_username"],
    MonitorType.MINECRAFT: ["address", "edition"],
}

_BOOL_FIELDS = {"verify_ssl", "ping_enabled", "tcp_enabled"}
_INT_FIELDS = {"port", "vmid", "timeout_seconds", "expect_status_below"}


def _build_config(monitor_type: MonitorType, form: dict) -> dict:
    config: dict = {}
    for field in MONITOR_TYPE_FIELDS[monitor_type]:
        raw = form.get(field)
        if field in _BOOL_FIELDS:
            config[field] = raw == "on" or raw == "true"
            continue
        if raw is None or raw == "":
            continue
        if field in _INT_FIELDS:
            config[field] = int(raw)
        else:
            config[field] = raw
    return config


@router.get("")
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Monitor).order_by(Monitor.sort_order, Monitor.id))
    monitors = list(result.scalars())

    latest_by_monitor = {}
    for monitor in monitors:
        latest = await db.scalar(
            select(CheckResult)
            .where(CheckResult.monitor_id == monitor.id)
            .order_by(CheckResult.checked_at.desc())
            .limit(1)
        )
        latest_by_monitor[monitor.id] = latest

    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {"monitors": monitors, "latest_by_monitor": latest_by_monitor},
    )


@router.get("/monitors/new")
async def monitor_new_form(request: Request):
    return templates.TemplateResponse(
        request,
        "admin/monitor_form.html",
        {"monitor": None, "monitor_types": list(MonitorType)},
    )


@router.post("/monitors/new")
async def monitor_new_submit(request: Request, db: AsyncSession = Depends(get_db)):
    form = dict(await request.form())
    monitor_type = MonitorType(form["type"])
    monitor = Monitor(
        name=form["name"],
        type=monitor_type,
        config=_build_config(monitor_type, form),
        check_interval_seconds=int(form.get("check_interval_seconds") or 60),
        failure_threshold=int(form.get("failure_threshold") or 1),
        enabled=form.get("enabled") == "on",
        show_on_status_page=form.get("show_on_status_page") == "on",
    )
    db.add(monitor)
    await db.commit()
    await db.refresh(monitor)
    if monitor.enabled:
        schedule_monitor(monitor)
    return RedirectResponse(url="/admin", status_code=303)


@router.get("/monitors/{monitor_id}/edit")
async def monitor_edit_form(
    monitor_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    monitor = await db.get(Monitor, monitor_id)
    return templates.TemplateResponse(
        request,
        "admin/monitor_form.html",
        {"monitor": monitor, "monitor_types": list(MonitorType)},
    )


@router.post("/monitors/{monitor_id}/edit")
async def monitor_edit_submit(
    monitor_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    form = dict(await request.form())
    monitor = await db.get(Monitor, monitor_id)
    monitor_type = MonitorType(form["type"])
    monitor.name = form["name"]
    monitor.type = monitor_type
    monitor.config = _build_config(monitor_type, form)
    monitor.check_interval_seconds = int(form.get("check_interval_seconds") or 60)
    monitor.failure_threshold = int(form.get("failure_threshold") or 1)
    monitor.enabled = form.get("enabled") == "on"
    monitor.show_on_status_page = form.get("show_on_status_page") == "on"
    await db.commit()

    unschedule_monitor(monitor.id)
    if monitor.enabled:
        schedule_monitor(monitor)
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/monitors/{monitor_id}/delete")
async def monitor_delete(monitor_id: int, db: AsyncSession = Depends(get_db)):
    monitor = await db.get(Monitor, monitor_id)
    if monitor is not None:
        await db.delete(monitor)
        await db.commit()
        unschedule_monitor(monitor_id)
    return RedirectResponse(url="/admin", status_code=303)


# --- Incidents ---


@router.get("/incidents")
async def incident_list(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Incident).options(selectinload(Incident.monitor)).order_by(Incident.started_at.desc())
    )
    incidents = list(result.scalars())
    return templates.TemplateResponse(request, "admin/incident_list.html", {"incidents": incidents})


@router.get("/incidents/new")
async def incident_new_form(request: Request, db: AsyncSession = Depends(get_db)):
    monitors = list((await db.execute(select(Monitor).order_by(Monitor.name))).scalars())
    return templates.TemplateResponse(
        request, "admin/incident_form.html", {"monitors": monitors}
    )


@router.post("/incidents/new")
async def incident_new_submit(request: Request, db: AsyncSession = Depends(get_db)):
    form = dict(await request.form())
    monitor_id = form.get("monitor_id")
    incident = Incident(
        monitor_id=int(monitor_id) if monitor_id else None,
        title=form["title"],
        description=form["description"],
        status=IncidentStatus(form.get("status") or IncidentStatus.INVESTIGATING),
        is_published=form.get("is_published") == "on",
    )
    db.add(incident)
    await db.commit()
    return RedirectResponse(url="/admin/incidents", status_code=303)


@router.get("/incidents/{incident_id}")
async def incident_detail(
    incident_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Incident)
        .options(selectinload(Incident.updates), selectinload(Incident.monitor))
        .where(Incident.id == incident_id)
    )
    incident = result.scalar_one()
    return templates.TemplateResponse(request, "admin/incident_detail.html", {"incident": incident})


@router.post("/incidents/{incident_id}/update")
async def incident_add_update(
    incident_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    form = dict(await request.form())
    incident = await db.get(Incident, incident_id)
    new_status = IncidentStatus(form["status"])
    db.add(
        IncidentUpdate(incident_id=incident_id, message=form["message"], status=new_status)
    )
    incident.status = new_status
    if new_status == IncidentStatus.RESOLVED and incident.resolved_at is None:
        incident.resolved_at = datetime.utcnow()
    await db.commit()
    return RedirectResponse(url=f"/admin/incidents/{incident_id}", status_code=303)


@router.post("/incidents/{incident_id}/publish_toggle")
async def incident_publish_toggle(incident_id: int, db: AsyncSession = Depends(get_db)):
    incident = await db.get(Incident, incident_id)
    incident.is_published = not incident.is_published
    await db.commit()
    return RedirectResponse(url=f"/admin/incidents/{incident_id}", status_code=303)


# --- Notification channels ---


@router.get("/notifications")
async def notification_list(request: Request, db: AsyncSession = Depends(get_db)):
    channels = list((await db.execute(select(NotificationChannel))).scalars())
    monitors = list((await db.execute(select(Monitor).order_by(Monitor.name))).scalars())
    links = list((await db.execute(select(MonitorNotification))).scalars())
    linked_pairs = {(link.monitor_id, link.channel_id) for link in links}
    return templates.TemplateResponse(
        request,
        "admin/notification_list.html",
        {"channels": channels, "monitors": monitors, "linked_pairs": linked_pairs},
    )


@router.post("/notifications/new")
async def notification_new_submit(request: Request, db: AsyncSession = Depends(get_db)):
    form = dict(await request.form())
    channel_type = NotificationType(form["type"])
    if channel_type == NotificationType.DISCORD_WEBHOOK:
        config = {"webhook_url": form["webhook_url"]}
    else:
        config = {"to_address": form["to_address"]}
    db.add(
        NotificationChannel(
            name=form["name"],
            type=channel_type,
            config=config,
            enabled=form.get("enabled") == "on",
        )
    )
    await db.commit()
    return RedirectResponse(url="/admin/notifications", status_code=303)


@router.post("/notifications/{channel_id}/delete")
async def notification_delete(channel_id: int, db: AsyncSession = Depends(get_db)):
    channel = await db.get(NotificationChannel, channel_id)
    if channel is not None:
        await db.delete(channel)
        await db.commit()
    return RedirectResponse(url="/admin/notifications", status_code=303)


@router.post("/notifications/link")
async def notification_link_toggle(request: Request, db: AsyncSession = Depends(get_db)):
    form = dict(await request.form())
    monitor_id = int(form["monitor_id"])
    channel_id = int(form["channel_id"])
    existing = await db.get(MonitorNotification, (monitor_id, channel_id))
    if existing:
        await db.delete(existing)
    else:
        db.add(MonitorNotification(monitor_id=monitor_id, channel_id=channel_id))
    await db.commit()
    return RedirectResponse(url="/admin/notifications", status_code=303)

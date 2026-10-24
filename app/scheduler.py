import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app import db as db_module
from app.checkers import run_check
from app.models import CheckResult, CheckStatus, Monitor, MonitorNotification, MonitorType
from app.notifications import notify
from app.pagespeed import measure_pagespeed

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

CHECK_JOB_PREFIX = "monitor-check-"
PAGESPEED_JOB_PREFIX = "monitor-pagespeed-"


async def run_monitor_check(monitor_id: int) -> None:
    async with db_module.async_session_maker() as db:
        monitor = await db.get(Monitor, monitor_id)
        if monitor is None or not monitor.enabled:
            return

        outcome = await run_check(monitor.type, monitor.config)

        db.add(
            CheckResult(
                monitor_id=monitor.id,
                status=outcome.status,
                response_time_ms=outcome.response_time_ms,
                detail=outcome.detail,
            )
        )

        previous_confirmed_status = monitor.last_status
        status_changed_to_down = False
        status_changed_to_up = False

        if outcome.status == CheckStatus.DOWN:
            monitor.consecutive_failures += 1
            if (
                monitor.consecutive_failures >= monitor.failure_threshold
                and previous_confirmed_status != CheckStatus.DOWN
            ):
                monitor.last_status = CheckStatus.DOWN
                status_changed_to_down = True
        else:
            if previous_confirmed_status == CheckStatus.DOWN:
                status_changed_to_up = True
            monitor.consecutive_failures = 0
            monitor.last_status = CheckStatus.UP

        await db.commit()

        if status_changed_to_down or status_changed_to_up:
            await _send_status_notifications(monitor_id, up=status_changed_to_up)


async def _send_status_notifications(monitor_id: int, *, up: bool) -> None:
    async with db_module.async_session_maker() as db:
        result = await db.execute(
            select(Monitor)
            .options(
                selectinload(Monitor.notification_links).selectinload(
                    MonitorNotification.channel
                )
            )
            .where(Monitor.id == monitor_id)
        )
        monitor = result.scalar_one_or_none()
        if monitor is None:
            return
        channels = [link.channel for link in monitor.notification_links if link.channel.enabled]

        title = f"✅ {monitor.name} は復旧しました" if up else f"🔴 {monitor.name} で障害を検知しました"
        description = (
            f"{monitor.name} ({monitor.type.value}) が正常に応答しています。"
            if up
            else f"{monitor.name} ({monitor.type.value}) への接続に {monitor.failure_threshold} 回連続で失敗しました。"
        )
        for channel in channels:
            await notify(
                db,
                channel,
                title=title,
                description=description,
                status="up" if up else "down",
            )


async def run_pagespeed_check(monitor_id: int) -> None:
    async with db_module.async_session_maker() as db:
        monitor = await db.get(Monitor, monitor_id)
        if monitor is None or not monitor.enabled or monitor.type != MonitorType.WEBPAGE:
            return
        await measure_pagespeed(db, monitor)


def schedule_monitor(monitor: Monitor) -> None:
    job_id = f"{CHECK_JOB_PREFIX}{monitor.id}"
    scheduler.add_job(
        run_monitor_check,
        trigger=IntervalTrigger(seconds=monitor.check_interval_seconds),
        args=[monitor.id],
        id=job_id,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    if monitor.type == MonitorType.WEBPAGE:
        pagespeed_job_id = f"{PAGESPEED_JOB_PREFIX}{monitor.id}"
        scheduler.add_job(
            run_pagespeed_check,
            trigger=CronTrigger(hour=3, minute=0),
            args=[monitor.id],
            id=pagespeed_job_id,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )


def unschedule_monitor(monitor_id: int) -> None:
    for prefix in (CHECK_JOB_PREFIX, PAGESPEED_JOB_PREFIX):
        job_id = f"{prefix}{monitor_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)


async def load_all_monitors_into_scheduler() -> None:
    async with db_module.async_session_maker() as db:
        result = await db.execute(select(Monitor).where(Monitor.enabled.is_(True)))
        for monitor in result.scalars():
            schedule_monitor(monitor)

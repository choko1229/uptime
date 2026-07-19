from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CheckResult, CheckStatus


async def calculate_uptime_percent(
    db: AsyncSession, monitor_id: int, days: int
) -> float | None:
    """Time-weighted uptime percentage over the trailing `days` days.

    Each CheckResult's status is assumed to hold from its own timestamp until
    the next check (or until now for the last one), so uptime is downtime-seconds
    subtracted from the window, not a simple up-check / total-check ratio.
    """
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=days)

    prior_result = await db.scalar(
        select(CheckResult)
        .where(CheckResult.monitor_id == monitor_id, CheckResult.checked_at < period_start)
        .order_by(CheckResult.checked_at.desc())
        .limit(1)
    )

    in_window = await db.execute(
        select(CheckResult)
        .where(
            CheckResult.monitor_id == monitor_id,
            CheckResult.checked_at >= period_start,
            CheckResult.checked_at <= period_end,
        )
        .order_by(CheckResult.checked_at.asc())
    )
    results = list(in_window.scalars())

    if prior_result is None and not results:
        return None

    timeline: list[tuple[datetime, CheckStatus]] = []
    if prior_result is not None:
        timeline.append((period_start, prior_result.status))
    for r in results:
        timeline.append((r.checked_at, r.status))

    downtime = timedelta()
    total = timedelta()
    for i, (seg_start, seg_status) in enumerate(timeline):
        seg_end = timeline[i + 1][0] if i + 1 < len(timeline) else period_end
        if seg_end <= seg_start:
            continue
        duration = seg_end - seg_start
        total += duration
        if seg_status == CheckStatus.DOWN:
            downtime += duration

    if total.total_seconds() <= 0:
        return None

    uptime_ratio = 1 - (downtime.total_seconds() / total.total_seconds())
    return round(max(0.0, min(100.0, uptime_ratio * 100)), 2)

from datetime import datetime, timedelta

import pytest

from app.models import CheckResult, CheckStatus, Monitor, MonitorType
from app.uptime_calc import calculate_uptime_percent

pytestmark = pytest.mark.asyncio


async def test_uptime_with_partial_history(db_session):
    monitor = Monitor(name="target", type=MonitorType.VPS, config={"host": "1.2.3.4"})
    db_session.add(monitor)
    await db_session.commit()
    await db_session.refresh(monitor)

    now = datetime.utcnow()
    db_session.add_all(
        [
            CheckResult(
                monitor_id=monitor.id,
                checked_at=now - timedelta(days=10),
                status=CheckStatus.UP,
                detail={},
            ),
            CheckResult(
                monitor_id=monitor.id,
                checked_at=now - timedelta(days=5),
                status=CheckStatus.DOWN,
                detail={},
            ),
            CheckResult(
                monitor_id=monitor.id,
                checked_at=now - timedelta(days=3),
                status=CheckStatus.UP,
                detail={},
            ),
        ]
    )
    await db_session.commit()

    # 2 days of downtime out of the 10 days we actually have history for.
    uptime_10 = await calculate_uptime_percent(db_session, monitor.id, 10)
    assert uptime_10 == pytest.approx(80.0, abs=0.5)

    # No data exists before day -10, so a wider 30-day window is still only
    # backed by 10 days of real history and should match the 10-day figure.
    uptime_30 = await calculate_uptime_percent(db_session, monitor.id, 30)
    assert uptime_30 == pytest.approx(80.0, abs=0.5)


async def test_uptime_with_no_data_returns_none(db_session):
    assert await calculate_uptime_percent(db_session, 999, 30) is None


async def test_uptime_fully_up(db_session):
    monitor = Monitor(name="target", type=MonitorType.VPS, config={"host": "1.2.3.4"})
    db_session.add(monitor)
    await db_session.commit()
    await db_session.refresh(monitor)

    now = datetime.utcnow()
    db_session.add(
        CheckResult(
            monitor_id=monitor.id,
            checked_at=now - timedelta(days=5),
            status=CheckStatus.UP,
            detail={},
        )
    )
    await db_session.commit()

    uptime = await calculate_uptime_percent(db_session, monitor.id, 30)
    assert uptime == 100.0

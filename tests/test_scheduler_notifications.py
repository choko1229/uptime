from unittest.mock import AsyncMock, patch

import pytest

import app.scheduler as scheduler
from app.checkers.base import CheckOutcome
from app.models import (
    CheckStatus,
    Monitor,
    MonitorNotification,
    MonitorType,
    NotificationChannel,
    NotificationType,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def flaky_monitor(db_session):
    monitor = Monitor(
        name="Flaky site",
        type=MonitorType.WEBPAGE,
        config={"url": "https://flaky.example.com"},
        failure_threshold=3,
    )
    db_session.add(monitor)
    await db_session.commit()
    await db_session.refresh(monitor)

    channel = NotificationChannel(
        name="Test discord",
        type=NotificationType.DISCORD_WEBHOOK,
        config={"webhook_url": "https://discord.com/api/webhooks/x/y"},
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)

    db_session.add(MonitorNotification(monitor_id=monitor.id, channel_id=channel.id))
    await db_session.commit()
    return monitor.id


async def test_notification_fires_once_threshold_crossed_and_not_before(flaky_monitor):
    down = CheckOutcome(status=CheckStatus.DOWN, response_time_ms=10, detail={})
    sent = []

    async def fake_notify(channel, *, title, description, status):
        sent.append(status)

    with patch("app.scheduler.run_check", new=AsyncMock(return_value=down)), patch(
        "app.scheduler.notify", new=fake_notify
    ):
        await scheduler.run_monitor_check(flaky_monitor)
        await scheduler.run_monitor_check(flaky_monitor)
        assert sent == []  # below failure_threshold=3

        await scheduler.run_monitor_check(flaky_monitor)
        assert sent == ["down"]  # threshold just crossed

        await scheduler.run_monitor_check(flaky_monitor)
        assert sent == ["down"]  # still down, must not spam


async def test_recovery_notification_fires_once(flaky_monitor):
    down = CheckOutcome(status=CheckStatus.DOWN, response_time_ms=10, detail={})
    up = CheckOutcome(status=CheckStatus.UP, response_time_ms=10, detail={})
    sent = []

    async def fake_notify(channel, *, title, description, status):
        sent.append(status)

    with patch("app.scheduler.run_check", new=AsyncMock(return_value=down)), patch(
        "app.scheduler.notify", new=fake_notify
    ):
        for _ in range(3):
            await scheduler.run_monitor_check(flaky_monitor)
    assert sent == ["down"]

    with patch("app.scheduler.run_check", new=AsyncMock(return_value=up)), patch(
        "app.scheduler.notify", new=fake_notify
    ):
        await scheduler.run_monitor_check(flaky_monitor)
        await scheduler.run_monitor_check(flaky_monitor)
    assert sent == ["down", "up"]

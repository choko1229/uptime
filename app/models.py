import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class MonitorType(str, enum.Enum):
    PROXMOX_VM = "proxmox_vm"
    VPS = "vps"
    WEBPAGE = "webpage"
    DISCORD_BOT = "discord_bot"
    MINECRAFT = "minecraft"


class CheckStatus(str, enum.Enum):
    UP = "up"
    DOWN = "down"


class IncidentStatus(str, enum.Enum):
    INVESTIGATING = "investigating"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class NotificationType(str, enum.Enum):
    DISCORD_WEBHOOK = "discord_webhook"
    EMAIL = "email"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AppSettings(Base):
    """Single-row table (id is always 1) holding app-wide settings editable via /admin/settings."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    site_title: Mapped[str] = mapped_column(String(128), default="Uptime Monitor")
    pagespeed_api_key: Mapped[str] = mapped_column(String(255), default="")
    smtp_host: Mapped[str] = mapped_column(String(255), default="")
    smtp_port: Mapped[int] = mapped_column(Integer, default=587)
    smtp_username: Mapped[str] = mapped_column(String(255), default="")
    smtp_password: Mapped[str] = mapped_column(String(255), default="")
    smtp_from_address: Mapped[str] = mapped_column(String(255), default="")
    smtp_use_tls: Mapped[bool] = mapped_column(Boolean, default=True)


class Monitor(Base):
    __tablename__ = "monitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[MonitorType] = mapped_column(Enum(MonitorType))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    check_interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    failure_threshold: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    show_on_status_page: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_status: Mapped[CheckStatus | None] = mapped_column(Enum(CheckStatus), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    check_results: Mapped[list["CheckResult"]] = relationship(
        back_populates="monitor", cascade="all, delete-orphan"
    )
    incidents: Mapped[list["Incident"]] = relationship(back_populates="monitor")
    notification_links: Mapped[list["MonitorNotification"]] = relationship(
        back_populates="monitor", cascade="all, delete-orphan"
    )
    pagespeed_results: Mapped[list["PageSpeedResult"]] = relationship(
        back_populates="monitor", cascade="all, delete-orphan"
    )


class CheckResult(Base):
    __tablename__ = "check_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("monitors.id"), index=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
    status: Mapped[CheckStatus] = mapped_column(Enum(CheckStatus))
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)

    monitor: Mapped["Monitor"] = relationship(back_populates="check_results")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monitor_id: Mapped[int | None] = mapped_column(
        ForeignKey("monitors.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus), default=IncidentStatus.INVESTIGATING
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    monitor: Mapped["Monitor | None"] = relationship(back_populates="incidents")
    updates: Mapped[list["IncidentUpdate"]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentUpdate.created_at",
    )


class IncidentUpdate(Base):
    __tablename__ = "incident_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[IncidentStatus] = mapped_column(Enum(IncidentStatus))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    incident: Mapped["Incident"] = relationship(back_populates="updates")


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    monitor_links: Mapped[list["MonitorNotification"]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )


class MonitorNotification(Base):
    __tablename__ = "monitor_notifications"

    monitor_id: Mapped[int] = mapped_column(ForeignKey("monitors.id"), primary_key=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("notification_channels.id"), primary_key=True
    )

    monitor: Mapped["Monitor"] = relationship(back_populates="notification_links")
    channel: Mapped["NotificationChannel"] = relationship(back_populates="monitor_links")


class PageSpeedResult(Base):
    __tablename__ = "pagespeed_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("monitors.id"), index=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    performance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accessibility_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    best_practices_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seo_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)

    monitor: Mapped["Monitor"] = relationship(back_populates="pagespeed_results")

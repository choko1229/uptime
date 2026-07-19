"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

monitor_type_enum = sa.Enum(
    "proxmox_vm", "vps", "webpage", "discord_bot", "minecraft", name="monitortype"
)
check_status_enum = sa.Enum("up", "down", name="checkstatus")
incident_status_enum = sa.Enum(
    "investigating", "monitoring", "resolved", name="incidentstatus"
)
notification_type_enum = sa.Enum(
    "discord_webhook", "email", name="notificationtype"
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "monitors",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("type", monitor_type_enum, nullable=False),
        sa.Column("config", sa.JSON, nullable=False),
        sa.Column("check_interval_seconds", sa.Integer, nullable=False, server_default="60"),
        sa.Column("failure_threshold", sa.Integer, nullable=False, server_default="1"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("show_on_status_page", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("consecutive_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_status", check_status_enum, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "check_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "monitor_id", sa.Integer, sa.ForeignKey("monitors.id"), nullable=False, index=True
        ),
        sa.Column("checked_at", sa.DateTime, server_default=sa.func.now(), index=True),
        sa.Column("status", check_status_enum, nullable=False),
        sa.Column("response_time_ms", sa.Integer, nullable=True),
        sa.Column("detail", sa.JSON, nullable=False),
    )

    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "monitor_id", sa.Integer, sa.ForeignKey("monitors.id"), nullable=True, index=True
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column(
            "status", incident_status_enum, nullable=False, server_default="investigating"
        ),
        sa.Column("is_published", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "incident_updates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "incident_id",
            sa.Integer,
            sa.ForeignKey("incidents.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("status", incident_status_enum, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "notification_channels",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("type", notification_type_enum, nullable=False),
        sa.Column("config", sa.JSON, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "monitor_notifications",
        sa.Column("monitor_id", sa.Integer, sa.ForeignKey("monitors.id"), primary_key=True),
        sa.Column(
            "channel_id",
            sa.Integer,
            sa.ForeignKey("notification_channels.id"),
            primary_key=True,
        ),
    )

    op.create_table(
        "pagespeed_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "monitor_id", sa.Integer, sa.ForeignKey("monitors.id"), nullable=False, index=True
        ),
        sa.Column("measured_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("performance_score", sa.Integer, nullable=True),
        sa.Column("accessibility_score", sa.Integer, nullable=True),
        sa.Column("best_practices_score", sa.Integer, nullable=True),
        sa.Column("seo_score", sa.Integer, nullable=True),
        sa.Column("raw", sa.JSON, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("pagespeed_results")
    op.drop_table("monitor_notifications")
    op.drop_table("notification_channels")
    op.drop_table("incident_updates")
    op.drop_table("incidents")
    op.drop_table("check_results")
    op.drop_table("monitors")
    op.drop_table("users")

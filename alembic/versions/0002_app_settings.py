"""app settings table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("site_title", sa.String(128), nullable=False, server_default="Uptime Monitor"),
        sa.Column("pagespeed_api_key", sa.String(255), nullable=False, server_default=""),
        sa.Column("smtp_host", sa.String(255), nullable=False, server_default=""),
        sa.Column("smtp_port", sa.Integer, nullable=False, server_default="587"),
        sa.Column("smtp_username", sa.String(255), nullable=False, server_default=""),
        sa.Column("smtp_password", sa.String(255), nullable=False, server_default=""),
        sa.Column("smtp_from_address", sa.String(255), nullable=False, server_default=""),
        sa.Column("smtp_use_tls", sa.Boolean, nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_table("app_settings")

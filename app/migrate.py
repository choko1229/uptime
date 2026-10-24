from alembic import command
from alembic.config import Config


def run_migrations(database_url_sync: str) -> None:
    """Run Alembic migrations synchronously against the given sync DB URL."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url_sync)
    command.upgrade(config, "head")

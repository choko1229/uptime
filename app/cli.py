import asyncio

import click
from sqlalchemy import select

from app import db as db_module
from app.auth import hash_password
from app.models import User


async def _create_admin(username: str, password: str) -> None:
    if not db_module.is_configured():
        click.echo("Database is not configured yet. Complete /setup in the running app first.")
        raise SystemExit(1)
    async with db_module.async_session_maker() as db:
        existing = await db.scalar(select(User).where(User.username == username))
        if existing:
            existing.password_hash = hash_password(password)
            await db.commit()
            click.echo(f"Updated password for existing admin user '{username}'.")
            return
        db.add(User(username=username, password_hash=hash_password(password)))
        await db.commit()
        click.echo(f"Created admin user '{username}'.")


@click.group()
def cli() -> None:
    pass


@cli.command("create-admin")
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def create_admin(username: str, password: str) -> None:
    asyncio.run(_create_admin(username, password))


if __name__ == "__main__":
    cli()

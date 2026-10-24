import asyncio
import logging
import secrets

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text

from app import db as db_module
from app.auth import hash_password
from app.config import DEFAULT_SITE_TITLE
from app.migrate import run_migrations
from app.models import User
from app.runtime_config import build_database_url, save_database_config
from app.scheduler import load_all_monitors_into_scheduler

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


@router.get("/setup")
async def setup_form(request: Request):
    if db_module.is_configured():
        return RedirectResponse(url="/admin/login")
    return templates.TemplateResponse(
        request,
        "setup.html",
        {"site_title": DEFAULT_SITE_TITLE, "error": None, "form": {}},
    )


@router.post("/setup")
async def setup_submit(request: Request):
    if db_module.is_configured():
        return RedirectResponse(url="/admin/login", status_code=303)

    form = dict(await request.form())
    db_config = {
        "host": form.get("host", "").strip(),
        "port": form.get("port", "3306").strip() or "3306",
        "name": form.get("name", "").strip(),
        "user": form.get("user", "").strip(),
        "password": form.get("password", ""),
    }

    if not all([db_config["host"], db_config["name"], db_config["user"]]):
        return templates.TemplateResponse(
            request,
            "setup.html",
            {
                "site_title": DEFAULT_SITE_TITLE,
                "error": "ホスト・データベース名・ユーザー名は必須です。",
                "form": db_config,
            },
            status_code=400,
        )

    async_url = build_database_url(db_config)
    try:
        from sqlalchemy.ext.asyncio import create_async_engine

        test_engine = create_async_engine(async_url)
        try:
            async with test_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        finally:
            await test_engine.dispose()
    except Exception as exc:  # noqa: BLE001 - surfaced to the user as a form error
        return templates.TemplateResponse(
            request,
            "setup.html",
            {
                "site_title": DEFAULT_SITE_TITLE,
                "error": f"データベースに接続できませんでした: {exc}",
                "form": db_config,
            },
            status_code=400,
        )

    save_database_config(db_config)
    db_module.configure_database(async_url)

    sync_url = build_database_url(db_config, driver="mysql+pymysql")
    await asyncio.to_thread(run_migrations, sync_url)

    generated_password = None
    async with db_module.async_session_maker() as db:
        user_count = await db.scalar(select(func.count()).select_from(User))
        if user_count == 0:
            generated_password = secrets.token_urlsafe(12)
            db.add(User(username="admin", password_hash=hash_password(generated_password)))
            await db.commit()

    if generated_password:
        logger.warning("=" * 60)
        logger.warning("初期セットアップが完了しました。")
        logger.warning("管理者ユーザー名: admin")
        logger.warning("管理者パスワード: %s", generated_password)
        logger.warning("このパスワードは起動ログにのみ表示されます。ログイン後に変更してください。")
        logger.warning("=" * 60)

    await load_all_monitors_into_scheduler()

    return RedirectResponse(url="/admin/login?setup=done", status_code=303)

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import db as db_module
from app.config import DEFAULT_SITE_TITLE, SESSION_COOKIE_NAME
from app.migrate import run_migrations
from app.routers import admin, auth, public, setup
from app.runtime_config import build_database_url, get_or_create_secret_key, load_database_config
from app.scheduler import load_all_monitors_into_scheduler, scheduler

logging.basicConfig(level=logging.INFO)

secret_key = get_or_create_secret_key()

# Paths reachable before the database has been configured via /setup.
_SETUP_EXEMPT_PREFIXES = ("/setup", "/static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if db_module.is_configured():
        db_config = load_database_config()
        if db_config is not None:
            sync_url = build_database_url(db_config, driver="mysql+pymysql")
            await asyncio.to_thread(run_migrations, sync_url)
        await load_all_monitors_into_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title=DEFAULT_SITE_TITLE, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=secret_key, session_cookie=SESSION_COOKIE_NAME)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.middleware("http")
async def require_setup(request: Request, call_next):
    if not db_module.is_configured() and not request.url.path.startswith(_SETUP_EXEMPT_PREFIXES):
        return RedirectResponse(url="/setup")
    return await call_next(request)


app.include_router(setup.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(public.router)


if __name__ == "__main__":
    import os

    import uvicorn
    from dotenv import load_dotenv

    load_dotenv()
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)

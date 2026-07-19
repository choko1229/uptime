from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import authenticate, login_user, logout_user
from app.db import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/admin/login")
async def login_form(request: Request):
    return templates.TemplateResponse(
        request, "admin/login.html", {"error": None}
    )


@router.post("/admin/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate(db, username, password)
    if user is None:
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            {"error": "ユーザー名またはパスワードが違います"},
            status_code=401,
        )
    login_user(request, user)
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/logout")
async def logout(request: Request):
    logout_user(request)
    return RedirectResponse(url="/admin/login", status_code=303)

from fastapi import HTTPException, Request


async def require_admin(request: Request) -> str:
    username = request.session.get("username")
    if username is None:
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})
    return username

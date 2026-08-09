from urllib import response

from fastapi import APIRouter, Request, Depends, Form, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db import get_db
from deps.auth import get_current_user_optional
from core.security import verify_password, create_access_token, hash_password
from models.user import User
from core.device_loader import load_devices
from core.audit_logger import log_action

router = APIRouter(prefix="/ui", tags=["ui"])
templates = Jinja2Templates(directory="ui/templates")
templates.env.cache.clear()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    log_action(
        None,
        "page_view",
        "Viewed login page",
        request,
        category="navigation",
    )

    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        log_action(
            None,
            "login_failed",
            "Invalid credentials",
            request,
            category="authentication",
        )
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"},
            status_code=401,
        )

    token = create_access_token({"sub": str(user.id), "role": user.role})
    log_action(
        user,
        "login_success",
        "Logged in successfully",
        request,
        category="authentication",
    )

    response = RedirectResponse(url="http://localhost:8000/ui/devices", status_code=302)
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=False,  # set True in production
        samesite="lax",
    )
    return response

@router.get("/logout")
async def logout(
    request: Request,
    current_user: User | None = Depends(get_current_user_optional)
):
    # Log BEFORE clearing the session
    if current_user:
        log_action(
            current_user,
            "logout",
            f"User {current_user.username} logged out",
            request,
            category="authentication",
        )
    else:
        # Anonymous logout attempt
        log_action(
            None,
            "logout",
            "Anonymous user attempted logout",
            request,
            category="",
        )

    # Clear session cookie
    response = RedirectResponse("/ui/login")
    response.delete_cookie("session")
    return response


# @router.get("/ui/restore-admin")
# async def restore_admin(db: AsyncSession = Depends(get_db)):
#     stmt = select(User)
#     result = await db.execute(stmt)
#     users = result.scalars().all()

#     if not users:
#         return {"error": "No users exist"}

#     # Promote first user to admin
#     user = users[0]
#     user.role = "admin"
#     await db.commit()

#     return {"status": "Admin restored", "username": user.username}

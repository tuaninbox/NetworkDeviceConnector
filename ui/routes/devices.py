from urllib import response

from fastapi import APIRouter, Request, Depends, Form, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db import get_db
from deps.auth import get_current_user_optional
from core.security import verify_password, create_access_token, hash_password
from models.account import Account
from core.device_loader import load_devices
from core.audit_logger import log_action

router = APIRouter(prefix="/ui", tags=["ui"])
templates = Jinja2Templates(directory="ui/templates")
templates.env.cache.clear()

@router.get("/devices", response_class=HTMLResponse)
async def devices_page(
    request: Request,
    current_user: Account | None = Depends(get_current_user_optional),
):
    if current_user is None:
        return RedirectResponse("/ui/login")

    # Load devices from backend API
    
    api_url = f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/api/devices/"

# Forward user cookies to API
    cookies = request.cookies

    api_devices = await request.app.state.http_client.get(
        api_url,
        cookies=cookies
    )

    devices = api_devices.json()
    # print(devices)

    return templates.TemplateResponse(
        "devices.html",
        {
            "request": request,
            "current_user": current_user,
            "devices": devices,
        },
    )


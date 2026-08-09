# ui/requests.py
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update

from core.db import get_db
from deps.auth import get_current_user_optional
from models.user import User
from core.audit_logger import log_action

router = APIRouter(prefix="/ui", tags=["ui"])
templates = Jinja2Templates(directory="ui/templates")
templates.env.cache.clear()


# ---------------------------
# MAIN PAGE
# ---------------------------
@router.get("/requests", response_class=HTMLResponse)
async def requests_page(
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if current_user is None:
        log_action(
            current_user,
            "request_view",
            "Redirected to login page due to unauthenticated access attempt",
            request,
            category="Request"
        )
        return RedirectResponse(url="/ui/login")
    
    stmt = select(RequestModel)
    result = await db.execute(stmt)
    requests = result.scalars().all()

    return templates.TemplateResponse(
        "requests.html",
        {"request": request, "requests": requests, "current_user": current_user},
    )


# ---------------------------
# DELETE CONFIRM MODAL
# ---------------------------
@router.get("/requests/{req_id}/delete-confirm", response_class=HTMLResponse)
async def delete_confirm_modal(
    req_id: int,
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RequestModel).where(RequestModel.id == req_id)
    result = await db.execute(stmt)
    req = result.scalar_one_or_none()

    if req is None:
        return HTMLResponse("Not found", status_code=404)

    if req.owner_id != current_user.id:
        return HTMLResponse("Forbidden", status_code=403)

    return templates.TemplateResponse(
        "partials/delete_confirm.html",
        {"request": request, "req": req},
    )


# ---------------------------
# DELETE REQUEST
# ---------------------------
@router.delete("/requests/{req_id}", response_class=HTMLResponse)
async def delete_request(
    req_id: int,
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RequestModel).where(RequestModel.id == req_id)
    result = await db.execute(stmt)
    req = result.scalar_one_or_none()

    if req is None:
        return HTMLResponse("Not found", status_code=404)

    if req.owner_id != current_user.id:
        return HTMLResponse("Forbidden", status_code=403)

    await db.execute(delete(RequestModel).where(RequestModel.id == req_id))
    await db.commit()

    log_action(current_user, "request_delete", f"Deleted request {req_id}", request)

    # Return updated table
    stmt = select(RequestModel)
    result = await db.execute(stmt)
    requests = result.scalars().all()

    return templates.TemplateResponse(
        "partials/requests_table.html",
        {"request": request, "requests": requests, "current_user": current_user},
    )


# ---------------------------
# APPROVE MODAL
# ---------------------------
@router.get("/requests/{req_id}/approve-modal", response_class=HTMLResponse)
async def approve_modal(
    req_id: int,
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RequestModel).where(RequestModel.id == req_id)
    result = await db.execute(stmt)
    req = result.scalar_one_or_none()

    if req is None:
        return HTMLResponse("Not found", status_code=404)

    if req.owner_id == current_user.id:
        return HTMLResponse("You cannot approve your own request", status_code=403)

    return templates.TemplateResponse(
        "partials/approve_modal.html",
        {"request": request, "req": req},
    )


# ---------------------------
# APPROVE REQUEST
# ---------------------------
@router.post("/requests/{req_id}/approve", response_class=HTMLResponse)
async def approve_request(
    req_id: int,
    request: Request,
    justification: str = Form(...),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RequestModel).where(RequestModel.id == req_id)
    result = await db.execute(stmt)
    req = result.scalar_one_or_none()

    if req is None:
        return HTMLResponse("Not found", status_code=404)

    if req.owner_id == current_user.id:
        return HTMLResponse("Cannot approve your own request", status_code=403)

    await db.execute(
        update(RequestModel)
        .where(RequestModel.id == req_id)
        .values(status="approved", justification=justification)
    )
    await db.commit()

    log_action(current_user, "request_approve", f"Approved request {req_id}", request)

    stmt = select(RequestModel)
    result = await db.execute(stmt)
    requests = result.scalars().all()

    return templates.TemplateResponse(
        "partials/requests_table.html",
        {"request": request, "requests": requests, "current_user": current_user},
    )


# ---------------------------
# REJECT REQUEST
# ---------------------------
@router.post("/requests/{req_id}/reject", response_class=HTMLResponse)
async def reject_request(
    req_id: int,
    request: Request,
    justification: str = Form(...),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RequestModel).where(RequestModel.id == req_id)
    result = await db.execute(stmt)
    req = result.scalar_one_or_none()

    if req is None:
        return HTMLResponse("Not found", status_code=404)

    if req.owner_id == current_user.id:
        return HTMLResponse("Cannot reject your own request", status_code=403)

    await db.execute(
        update(RequestModel)
        .where(RequestModel.id == req_id)
        .values(status="rejected", justification=justification)
    )
    await db.commit()

    log_action(current_user, "request_reject", f"Rejected request {req_id}", request)

    stmt = select(RequestModel)
    result = await db.execute(stmt)
    requests = result.scalars().all()

    return templates.TemplateResponse(
        "partials/requests_table.html",
        {"request": request, "requests": requests, "current_user": current_user},
    )

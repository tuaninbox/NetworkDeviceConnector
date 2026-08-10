from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db import get_db
from deps.auth import get_current_user_optional
from core.permissions import has_permission
from core.security import hash_password
from core.logging import log_event
from models.account import Account
from schemas.account import AccountRead, AccountCreate, AccountUpdate

router = APIRouter(prefix="/api", tags=["accounts"])


# ---------------------------------------------------------
# CREATE ACCOUNT
# ---------------------------------------------------------
@router.post("/accounts", response_model=AccountRead)
async def api_create_account(
    payload: AccountCreate,
    request: Request,
    current_user: Account | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    # Auth check
    if current_user is None or current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Admin access required")

    # Permission check
    roles = request.app.state.roles
    if not has_permission(current_user.role, "create_accounts", roles):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Password confirmation
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Username uniqueness
    stmt = select(Account).where(Account.username == payload.username)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create new account
    acc = Account(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        source=payload.source,
        profiles=payload.profiles or [],
    )

    db.add(acc)
    await db.commit()
    await db.refresh(acc)

    return acc



# ---------------------------------------------------------
# LIST ACCOUNTS
# ---------------------------------------------------------
@router.get("/accounts", response_model=list[AccountRead])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: Account | None = Depends(get_current_user_optional),
):
    stmt = select(Account)
    result = await db.execute(stmt)
    accounts = result.scalars().all()
    return accounts

# Edit Account
@router.post("/accounts/{user_id}", response_model=AccountRead)
async def api_edit_account(
    user_id: int,
    payload: AccountUpdate,
    request: Request,
    current_user: Account | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    # Auth check
    if current_user is None or current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Admin access required")

    # Fetch user
    stmt = select(Account).where(Account.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")

    # Prevent demoting last admin
    stmt = select(Account).where(Account.role == "admin")
    admins = (await db.execute(stmt)).scalars().all()
    if user.role == "admin" and payload.role != "admin" and len(admins) == 1:
        raise HTTPException(status_code=400, detail="Cannot change role of the last admin")

    # Username uniqueness
    if payload.username and payload.username != user.username:
        stmt = select(User).where(User.username == payload.username)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        user.username = payload.username

    # First/Last name update
    if payload.first_name is not None:
        user.first_name = payload.first_name

    if payload.last_name is not None:
        user.last_name = payload.last_name

    # Email update
    if payload.email:
        user.email = payload.email

    # Role update
    if payload.role:
        user.role = payload.role

    # Profiles update
    if payload.profiles is not None:
        user.profiles = payload.profiles

    # Password update
    if payload.new_password:
        if payload.new_password != payload.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        user.password_hash = hash_password(payload.new_password)

    await db.commit()
    await db.refresh(user)

    return user

# Get Account to edit
@router.get("/accounts/{user_id}", response_model=AccountRead)
async def api_get_account(
    user_id: int,
    current_user: Account | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if current_user is None or current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Admin access required")

    stmt = select(Account).where(Account.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Account not found")

    return user


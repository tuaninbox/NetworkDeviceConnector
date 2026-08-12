from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db import get_db
from deps.auth import get_current_user_optional, get_current_user
from core.permissions import has_permission
from core.security import hash_password, verify_password
from core.logging import log_event
from models.account import Account
from schemas.account import AccountRead, AccountCreate, AccountUpdate, AccountSelfUpdate

router = APIRouter(prefix="/api", tags=["accounts"])

# Admin Account Endpoinst
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

# ADMIN ENDPOINTS

# ---------------------------------------------------------
# EDIT ACCOUNTS
# ---------------------------------------------------------
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
    account = (await db.execute(stmt)).scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Prevent demoting last admin
    stmt = select(Account).where(Account.role == "admin")
    admins = (await db.execute(stmt)).scalars().all()
    if account.role == "admin" and payload.role != "admin" and len(admins) == 1:
        raise HTTPException(status_code=400, detail="Cannot change role of the last admin")

    # Username uniqueness
    if payload.username and payload.username != account.username:
        stmt = select(Account).where(Account.username == payload.username)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        account.username = payload.username

    # First/Last name update
    if payload.first_name is not None:
        account.first_name = payload.first_name

    if payload.last_name is not None:
        account.last_name = payload.last_name

    # Email update
    if payload.email:
        account.email = payload.email

    # Role update
    if payload.role:
        account.role = payload.role

    # Profiles update
    if payload.profiles is not None:
        account.profiles = payload.profiles

    # Password update
    if payload.new_password:
        if payload.new_password != payload.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        account.password_hash = hash_password(payload.new_password)

    await db.commit()
    await db.refresh(account)

    return account

# ---------------------------------------------------------
# VIEW SELF ACCOUNT - Need to be before get("/accounts/{user_id}")
# ---------------------------------------------------------
@router.get("/accounts/me", response_model=AccountRead)
async def api_get_self(current_user: Account = Depends(get_current_user)):
    return current_user

# ---------------------------------------------------------
# GET ACCOUNTS TO EDIT
# ---------------------------------------------------------
@router.get("/accounts/{user_id}", response_model=AccountRead)
async def api_get_account(
    user_id: int,
    current_user: Account | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if current_user is None or current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Admin access required")

    stmt = select(Account).where(Account.id == user_id)
    account = (await db.execute(stmt)).scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return account

# ---------------------------------------------------------
# CREATE ACCOUNTS
# ---------------------------------------------------------
@router.post("/accounts", response_model=AccountRead)
async def api_create_account(
    payload: AccountCreate,
    current_user: Account | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    # Auth check
    if current_user is None or current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Admin access required")

    # Password confirmation
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Username uniqueness
    stmt = select(Account).where(Account.username == payload.username)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create account
    new_account = Account(
        username=payload.username,
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        auth_source="local",
    )

    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)

    return new_account

# ---------------------------------------------------------
# DELETE ACCOUNTS
# ---------------------------------------------------------
@router.delete("/accounts/{user_id}", response_model=list[AccountRead])
async def api_delete_account(
    user_id: int,
    current_user: Account | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    # Must be admin
    if current_user is None or current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Admin access required")

    # Count admins BEFORE deleting
    stmt = select(Account).where(Account.role == "admin")
    admin_count = len((await db.execute(stmt)).scalars().all())


    # Fetch account
    stmt = select(Account).where(Account.id == user_id)
    account = (await db.execute(stmt)).scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Prevent deleting last admin
    if account.role == "admin" and admin_count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last admin account")

    # Delete
    await db.delete(account)
    await db.commit()

    # Return updated list
    stmt = select(Account)
    accounts = (await db.execute(stmt)).scalars().all()

    return accounts

# SELF ENDPOINTS

# ---------------------------------------------------------
# UPDATE SELF ACCOUNT
# ---------------------------------------------------------
@router.put("/accounts/{user_id}", response_model=AccountRead)
async def api_update_account_self(
    user_id: int,
    payload: AccountSelfUpdate,
    current_user: Account | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    # Must be logged in
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Only admin or self can update
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Fetch account
    stmt = select(Account).where(Account.id == user_id)
    account = (await db.execute(stmt)).scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Verify current password
    if not payload.current_password or not verify_password(payload.current_password, account.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Username uniqueness
    if payload.username and payload.username != account.username:
        stmt = select(Account).where(Account.username == payload.username)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        account.username = payload.username

    # First name update
    if payload.first_name is not None:
        account.first_name = payload.first_name

    # Last name update
    if payload.last_name is not None:
        account.last_name = payload.last_name

    # Email update
    if payload.email:
        account.email = payload.email

    # Password update
    if payload.new_password:
        if payload.new_password != payload.confirm_password:
            raise HTTPException(status_code=400, detail="New passwords do not match")
        account.password_hash = hash_password(payload.new_password)

    await db.commit()
    await db.refresh(account)

    return account


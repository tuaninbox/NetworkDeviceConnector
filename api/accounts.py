from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db import get_db
from deps.auth import get_current_user
from core.logging import log_event
from models.user import User
from models.account import Account
from schemas.account import AccountRead, AccountCreate

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


# ---------------------------------------------------------
# CREATE ACCOUNT (no device, no vault)
# ---------------------------------------------------------
@router.post("/", response_model=AccountRead)
async def create_account(
    request: Request,
    item: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    roles = request.app.state.roles

    if not has_permission(current_user.role, "create_accounts", roles):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Confirm password check
    if item.password != item.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    acc = Account(
        username=item.username,
        password_hash=hash_password(item.password),
        role=item.role,
        first_name=item.first_name,
        last_name=item.last_name,
        email=item.email,
        source=item.source,
        profiles=item.profiles,
    )

    db.add(acc)
    await db.commit()
    await db.refresh(acc)

    return AccountRead.model_validate(acc)


# ---------------------------------------------------------
# LIST ACCOUNTS
# ---------------------------------------------------------
@router.get("/", response_model=list[AccountRead])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Account)
    result = await db.execute(stmt)
    accounts = result.scalars().all()
    return accounts

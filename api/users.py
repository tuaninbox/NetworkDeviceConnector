from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db import get_db
from deps.auth import get_current_user
from models.user import User
from schemas.user import UserRead

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can list users")

    stmt = select(User)
    result = await db.execute(stmt)
    return result.scalars().all()

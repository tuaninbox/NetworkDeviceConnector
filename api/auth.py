from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db import get_db
from core.security import verify_password, create_access_token
from models.account import Account
from schemas.auth import LoginRequest, Token

router = APIRouter(prefix="/api", tags=["auth"])

# @router.post("/login", response_model=Token)
# async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
#     stmt = select(Account).where(Account.username == data.username)
#     result = await db.execute(stmt)
#     user = result.scalar_one_or_none()
#     if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
#     token = create_access_token({"sub": user.id, "role": user.role})
#     return Token(access_token=token)

@router.post("/login", response_model=Token)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Account).where(Account.username == data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    token = create_access_token({"sub": str(user.id), "role": user.role})

    return Token(access_token=token, token_type="bearer")

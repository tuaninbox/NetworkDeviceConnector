from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db import get_db
from core.security import verify_password, create_access_token
from models.account import Account
from schemas.auth import LoginRequest, Token
from core.security import (
    too_many_attempts,
    record_failed_attempt,
    clear_attempts
)



router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    ip = request.client.host
    username = data.username

    # Brute-force protection
    if await too_many_attempts(ip, username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later."
        )

    # Lookup user
    stmt = select(Account).where(Account.username == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # Invalid login
    if not user or not verify_password(data.password, user.password_hash):
        record_failed_attempt(ip, username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Successful login → clear failures
    clear_attempts(ip, username)

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return Token(access_token=token, token_type="bearer")

# @router.post("/login", response_model=Token)
# async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
#     stmt = select(Account).where(Account.username == data.username)
#     result = await db.execute(stmt)
#     user = result.scalar_one_or_none()
#     if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
#     token = create_access_token({"sub": user.id, "role": user.role})
#     return Token(access_token=token)

# @router.post("/login", response_model=Token)
# async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
#     stmt = select(Account).where(Account.username == data.username)
#     result = await db.execute(stmt)
#     user = result.scalar_one_or_none()

#     if not user or not verify_password(data.password, user.password_hash):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid credentials"
#         )

#     token = create_access_token({"sub": str(user.id), "role": user.role})

#     return Token(access_token=token, token_type="bearer")

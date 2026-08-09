from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.security import decode_token
from core.db import get_db
from models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # 1. Try cookie first (UI)
    token = request.cookies.get("session")
    if token:
        try:
            payload = decode_token(token)
            user_id = int(payload.get("sub"))
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token payload")

            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if user and user.is_active:
                return user

        except Exception as e:
            print("COOKIE DECODE ERROR:", e)  # TEMP DEBUG
            raise HTTPException(status_code=401, detail="Invalid session token")

    # 2. Fallback to Authorization header (API)
    try:
        token = await oauth2_scheme(request)
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user and user.is_active:
            return user

    except Exception as e:
        print("HEADER DECODE ERROR:", e)  # TEMP DEBUG
        raise HTTPException(status_code=401, detail="Unauthorized")

    raise HTTPException(status_code=401, detail="Unauthorized")

async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None

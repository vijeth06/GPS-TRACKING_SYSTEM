"""Auth Dependencies for FastAPI routes."""

from typing import List, Optional

from fastapi import Depends, Header, HTTPException

from backend.services.auth_service import AuthService


async def get_current_user(authorization: str = Header(default="", alias="Authorization")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    auth = AuthService()
    try:
        payload = auth.decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await auth.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


def require_roles(allowed_roles: List[str]):
    async def dependency(user: dict = Depends(get_current_user)) -> dict:
        role = user.get("role")
        if role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency

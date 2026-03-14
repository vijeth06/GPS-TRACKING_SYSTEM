"""Authentication Routes"""

from fastapi import APIRouter, HTTPException, Depends

from backend.api.schemas import LoginRequest, TokenResponse, UserResponse
from backend.services.auth_service import AuthService
from backend.services.auth_dependencies import get_current_user


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    auth = AuthService()
    user = await auth.authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth.create_access_token(user)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(**AuthService.to_public_user(user)),
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**AuthService.to_public_user(current_user))

"""Admin routes for users and teams."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.api.schemas import AdminUserCreate, AdminUserUpdate, TeamCreate, TeamResponse, UserResponse
from backend.services.admin_service import AdminService
from backend.services.auth_dependencies import require_roles
from backend.services.auth_service import UserRole


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=List[UserResponse])
async def list_users(current_user: dict = Depends(require_roles([UserRole.ADMIN]))):
    _ = current_user
    svc = AdminService()
    rows = await svc.list_users()
    return [UserResponse(**r) for r in rows]


@router.post("/users", response_model=UserResponse)
async def create_user(
    payload: AdminUserCreate,
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    _ = current_user
    svc = AdminService()
    try:
        row = await svc.create_user(payload.model_dump())
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to create user")
    return UserResponse(**row)


@router.put("/users/{username}", response_model=UserResponse)
async def update_user(
    username: str,
    payload: AdminUserUpdate,
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    _ = current_user
    svc = AdminService()
    row = await svc.update_user(username, payload.model_dump())
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**row)


@router.get("/teams", response_model=List[TeamResponse])
async def list_teams(current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR]))):
    _ = current_user
    svc = AdminService()
    return await svc.list_teams()


@router.post("/teams", response_model=TeamResponse)
async def create_team(
    payload: TeamCreate,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
):
    _ = current_user
    svc = AdminService()
    return await svc.create_team(payload.model_dump())


@router.delete("/teams/{team_id}")
async def delete_team(
    team_id: str,
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    _ = current_user
    svc = AdminService()
    ok = await svc.delete_team(team_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Team not found")
    return {"deleted": True}

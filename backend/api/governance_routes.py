"""Governance routes."""

from fastapi import APIRouter, Depends

from backend.api.schemas import GovernanceSettings, GovernanceSettingsResponse
from backend.services.auth_dependencies import require_roles
from backend.services.auth_service import UserRole
from backend.services.governance_service import GovernanceService


router = APIRouter(prefix="/governance", tags=["Governance"])


@router.get("/settings", response_model=GovernanceSettingsResponse)
async def get_governance_settings(
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER])),
):
    _ = current_user
    svc = GovernanceService()
    return await svc.get_settings()


@router.put("/settings", response_model=GovernanceSettingsResponse)
async def update_governance_settings(
    payload: GovernanceSettings,
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    svc = GovernanceService()
    return await svc.update_settings(payload.model_dump(), updated_by=current_user.get("username", "unknown"))

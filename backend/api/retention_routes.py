"""Retention/archive management routes."""

from fastapi import APIRouter, Depends

from backend.api.schemas import RetentionStatus, RetentionRunResult
from backend.services.auth_dependencies import require_roles
from backend.services.auth_service import UserRole
from backend.services.retention_service import retention_service


router = APIRouter(prefix="/retention", tags=["Retention"])


@router.get("/status", response_model=RetentionStatus)
async def get_retention_status(
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER])),
):
    _ = current_user
    return RetentionStatus(**retention_service.status())


@router.post("/run", response_model=RetentionRunResult)
async def run_retention_now(
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    _ = current_user
    result = await retention_service.run_once()
    return RetentionRunResult(**result)

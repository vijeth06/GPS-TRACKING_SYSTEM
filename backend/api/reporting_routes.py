"""Reporting routes."""

from fastapi import APIRouter, Depends

from backend.api.schemas import ReportingSummary
from backend.services.auth_dependencies import require_roles
from backend.services.auth_service import UserRole
from backend.services.reporting_service import ReportingService


router = APIRouter(prefix="/reporting", tags=["Reporting"])


@router.get("/summary", response_model=ReportingSummary)
async def get_reporting_summary(
    hours: int = 24,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER])),
):
    _ = current_user
    svc = ReportingService()
    return await svc.summary(hours)

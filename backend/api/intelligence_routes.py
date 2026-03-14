"""Advanced intelligence routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from backend.api.schemas import AnomalyInsight
from backend.services.auth_dependencies import require_roles
from backend.services.auth_service import UserRole
from backend.services.intelligence_service import IntelligenceService


router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


@router.get("/anomaly", response_model=AnomalyInsight)
async def anomaly_for_device(
    device_id: str,
    speed: float = Query(0.0),
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER])),
):
    _ = current_user
    svc = IntelligenceService()
    return await svc.compute_speed_anomaly(device_id=device_id, speed=speed, measured_at=datetime.utcnow())

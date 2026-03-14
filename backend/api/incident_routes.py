"""Incident investigation routes."""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.schemas import IncidentWorkspaceResponse, AlertResponse
from backend.services.auth_dependencies import require_roles
from backend.services.auth_service import UserRole
from backend.services.incident_service import IncidentService


router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("/open", response_model=list[AlertResponse])
async def get_open_incidents(
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER])),
):
    _ = current_user
    svc = IncidentService()
    return await svc.get_open_incidents(limit=limit)


@router.get("/{alert_id}/workspace", response_model=IncidentWorkspaceResponse)
async def get_incident_workspace(
    alert_id: str,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER])),
):
    _ = current_user
    svc = IncidentService()
    workspace = await svc.get_workspace(alert_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Incident alert {alert_id} not found")
    return IncidentWorkspaceResponse(**workspace)

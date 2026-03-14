"""
Alert Routes
============
API endpoints for alert management.

Endpoints:
    GET /alerts - Get all alerts
    GET /alerts/unacknowledged - Get unacknowledged alerts
    POST /alerts/{id}/acknowledge - Acknowledge an alert
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime, timedelta

from backend.api.schemas import AlertResponse, AlertResolve, AlertAssign, AlertEscalate
from backend.services.alert_service import AlertService
from backend.services.auth_dependencies import require_roles
from backend.services.auth_service import UserRole

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=List[AlertResponse], summary="Get all alerts")
async def get_alerts(
    device_id: Optional[str] = Query(None, description="Filter by device"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    start_time: Optional[datetime] = Query(None, description="Start of time range"),
    end_time: Optional[datetime] = Query(None, description="End of time range"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum alerts to return")
):
    """
    Get alerts with optional filters.
    
    Args:
        device_id: Filter by specific device
        alert_type: Filter by type (stationary_alert, speed_alert, geofence_alert)
        severity: Filter by severity (low, medium, high, critical)
        start_time: Filter by time range start
        end_time: Filter by time range end
        limit: Maximum number of alerts to return
        
    Returns:
        List of alerts matching the filters
    """
    # Default to last 24 hours if no time range specified
    if not end_time:
        end_time = datetime.utcnow()
    if not start_time:
        start_time = end_time - timedelta(hours=24)
    
    alert_service = AlertService()
    alerts = await alert_service.get_alerts(
        device_id=device_id,
        alert_type=alert_type,
        severity=severity,
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )
    return alerts


@router.get("/unacknowledged", response_model=List[AlertResponse], summary="Get unacknowledged alerts")
async def get_unacknowledged_alerts(
    limit: int = Query(50, ge=1, le=500)
):
    """
    Get all unacknowledged alerts.
    
    Returns:
        List of alerts that haven't been acknowledged yet
    """
    alert_service = AlertService()
    alerts = await alert_service.get_unacknowledged_alerts(limit=limit)
    return alerts


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse, summary="Acknowledge alert")
async def acknowledge_alert(alert_id: str):
    """
    Acknowledge an alert.
    
    Args:
        alert_id: ID of the alert to acknowledge
        
    Returns:
        Updated alert with acknowledgement status
    """
    alert_service = AlertService()
    alert = await alert_service.acknowledge_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    return alert


@router.post("/{alert_id}/resolve", response_model=AlertResponse, summary="Resolve alert")
async def resolve_alert(
    alert_id: str,
    payload: AlertResolve,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Resolve an alert and store lifecycle audit information."""
    alert_service = AlertService()
    alert = await alert_service.resolve_alert(alert_id, resolution_note=payload.resolution_note)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return alert


@router.post("/{alert_id}/assign", response_model=AlertResponse, summary="Assign alert")
async def assign_alert(
    alert_id: str,
    payload: AlertAssign,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Assign an alert to an operator with audit trail."""
    alert_service = AlertService()
    alert = await alert_service.assign_alert(
        alert_id=alert_id,
        assigned_to=payload.assigned_to,
        assigned_by=current_user.get("username", "unknown"),
        assignment_note=payload.assignment_note,
    )
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return alert


@router.post("/{alert_id}/escalate", response_model=AlertResponse, summary="Escalate alert")
async def escalate_alert(
    alert_id: str,
    payload: AlertEscalate,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Escalate alert severity and escalation level."""
    alert_service = AlertService()
    alert = await alert_service.escalate_alert(
        alert_id=alert_id,
        escalated_by=current_user.get("username", "unknown"),
        escalation_note=payload.escalation_note,
    )
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return alert


@router.get("/stats", summary="Get alert statistics")
async def get_alert_stats():
    """
    Get alert statistics.
    
    Returns:
        Statistics about alerts by type and severity
    """
    alert_service = AlertService()
    stats = await alert_service.get_alert_statistics()
    return stats

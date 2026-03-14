"""Notification routes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.api.schemas import (
    NotificationChannelConfig,
    NotificationChannelResponse,
    NotificationDispatchResult,
    NotificationTestRequest,
)
from backend.services.auth_dependencies import require_roles
from backend.services.auth_service import UserRole
from backend.services.notification_service import NotificationService


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/channels", response_model=List[NotificationChannelResponse])
async def list_channels(current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER]))):
    _ = current_user
    svc = NotificationService()
    return await svc.list_channels()


@router.post("/channels", response_model=NotificationChannelResponse)
async def upsert_channel(
    payload: NotificationChannelConfig,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
):
    _ = current_user
    svc = NotificationService()
    return await svc.upsert_channel(payload.model_dump())


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: str,
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    _ = current_user
    svc = NotificationService()
    ok = await svc.delete_channel(channel_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Channel not found")
    return {"deleted": True}


@router.post("/channels/{channel_id}/test", response_model=NotificationDispatchResult)
async def test_channel(
    channel_id: str,
    payload: NotificationTestRequest,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
):
    _ = current_user
    svc = NotificationService()
    result = await svc.send_test(channel_id, payload.message, payload.severity)
    if not result.get("provider") or result.get("provider") == "unknown":
        raise HTTPException(status_code=404, detail="Channel not found")
    return result

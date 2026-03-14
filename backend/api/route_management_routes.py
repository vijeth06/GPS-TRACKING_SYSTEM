"""Route management routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.schemas import RoutePlanCreate, RoutePlanResponse
from backend.services.auth_dependencies import require_roles
from backend.services.auth_service import UserRole
from backend.services.route_service import RouteService


router = APIRouter(prefix="/routes", tags=["Route Management"])


@router.get("", response_model=List[RoutePlanResponse])
async def list_routes(
    device_id: Optional[str] = Query(None),
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER])),
):
    _ = current_user
    svc = RouteService()
    return await svc.list_routes(device_id=device_id)


@router.post("", response_model=RoutePlanResponse)
async def create_route(
    payload: RoutePlanCreate,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
):
    _ = current_user
    svc = RouteService()
    return await svc.create_route(payload.model_dump())


@router.delete("/{route_id}")
async def delete_route(
    route_id: str,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
):
    _ = current_user
    svc = RouteService()
    ok = await svc.delete_route(route_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Route not found")
    return {"deleted": True}

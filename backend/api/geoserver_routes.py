"""Geoserver Integration Routes"""

from fastapi import APIRouter, Depends

from backend.api.schemas import (
    GeoserverSyncResult,
    GeoserverLayerInfo,
    GeoserverConfigStatus,
    GeoserverConfigUpdate,
    GeoserverEndpointHealth,
    GeoserverDiscoveredLayers,
)
from backend.services.geoserver_service import GeoserverService
from backend.services.auth_dependencies import require_roles
from backend.services.auth_service import UserRole


router = APIRouter(prefix="/geoserver", tags=["GeoServer"])


@router.get("/layers", response_model=list[GeoserverLayerInfo])
async def list_layers(
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER]))
):
    _ = current_user
    svc = GeoserverService()
    return await svc.list_layers()


@router.get("/config", response_model=GeoserverConfigStatus)
async def get_geoserver_config(
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER]))
):
    _ = current_user
    svc = GeoserverService()
    return GeoserverConfigStatus(**(await svc.config_status()))


@router.get("/health", response_model=GeoserverEndpointHealth)
async def get_geoserver_health(
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER]))
):
    _ = current_user
    svc = GeoserverService()
    return GeoserverEndpointHealth(**(await svc.check_endpoint_health()))


@router.get("/discover", response_model=GeoserverDiscoveredLayers)
async def discover_geoserver_layers(
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER]))
):
    _ = current_user
    svc = GeoserverService()
    return GeoserverDiscoveredLayers(**(await svc.discover_layers()))


@router.post("/discover/apply", response_model=GeoserverConfigStatus)
async def discover_and_apply_layers(
    current_user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    _ = current_user
    svc = GeoserverService()
    discovered = await svc.discover_layers()
    return GeoserverConfigStatus(**(await svc.update_layer_names(discovered.get("layer_names", []))))


@router.put("/config/layers", response_model=GeoserverConfigStatus)
async def update_geoserver_layers(
    payload: GeoserverConfigUpdate,
    current_user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    _ = current_user
    svc = GeoserverService()
    return GeoserverConfigStatus(**(await svc.update_layer_names(payload.layer_names)))


@router.delete("/cache")
async def clear_geoserver_cache(
    current_user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    _ = current_user
    svc = GeoserverService()
    return await svc.clear_layer_cache()


@router.post("/sync", response_model=GeoserverSyncResult)
async def sync_layers(
    current_user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    svc = GeoserverService()
    return await svc.sync_layers_to_geofences()

"""Geoserver Integration Routes"""

from fastapi import APIRouter

from backend.api.schemas import GeoserverSyncResult, GeoserverLayerInfo
from backend.services.geoserver_service import GeoserverService


router = APIRouter(prefix="/geoserver", tags=["GeoServer"])


@router.get("/layers", response_model=list[GeoserverLayerInfo])
async def list_layers():
    svc = GeoserverService()
    return await svc.list_layers()


@router.post("/sync", response_model=GeoserverSyncResult)
async def sync_layers():
    svc = GeoserverService()
    return await svc.sync_layers_to_geofences()

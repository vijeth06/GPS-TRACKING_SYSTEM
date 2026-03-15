"""Ingestion Routes"""

from fastapi import APIRouter, Header, Depends

from backend.api.schemas import (
    RawGPSPacket,
    IngestionResult,
    IngestionStatus,
    StreamListenerStatus,
    StreamListenerStartRequest,
)
from backend.services.ingestion_service import ingestion_service
from backend.services.security_service import verify_packet_ingest_auth
from backend.services.stream_listener_service import stream_listener_service
from backend.services.auth_dependencies import require_roles
from backend.services.auth_service import UserRole


router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post("/raw", response_model=IngestionResult)
async def ingest_raw_packet(
    packet: RawGPSPacket,
    x_ingest_token: str = Header(default="", alias="X-Ingest-Token"),
    x_device_key: str = Header(default="", alias="X-Device-Key"),
):
    await verify_packet_ingest_auth(packet=packet, x_ingest_token=x_ingest_token, x_device_key=x_device_key)
    result = await ingestion_service.enqueue(packet)
    return IngestionResult(**result)


@router.get("/status", response_model=IngestionStatus)
async def get_ingestion_status():
    return IngestionStatus(**ingestion_service.status())


@router.get("/stream/status", response_model=StreamListenerStatus)
async def get_stream_status(
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER]))
):
    _ = current_user
    return StreamListenerStatus(**stream_listener_service.status())


@router.post("/stream/start", response_model=StreamListenerStatus)
async def start_stream_listener(
    payload: StreamListenerStartRequest,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR]))
):
    _ = current_user
    status = await stream_listener_service.start(
        protocol=payload.protocol,
        host=payload.host,
        port=payload.port,
        dataset_profile=payload.dataset_profile,
    )
    return StreamListenerStatus(**status)


@router.post("/stream/stop", response_model=StreamListenerStatus)
async def stop_stream_listener(
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR]))
):
    _ = current_user
    status = await stream_listener_service.stop()
    return StreamListenerStatus(**status)

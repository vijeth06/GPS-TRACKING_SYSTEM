"""Ingestion Routes"""

from fastapi import APIRouter, Header

from backend.api.schemas import RawGPSPacket, IngestionResult, IngestionStatus
from backend.services.ingestion_service import ingestion_service
from backend.services.security_service import verify_packet_ingest_auth


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

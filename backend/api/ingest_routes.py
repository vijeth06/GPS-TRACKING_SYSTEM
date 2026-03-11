"""Ingestion Routes"""

from fastapi import APIRouter, Depends

from backend.api.schemas import RawGPSPacket, IngestionResult, IngestionStatus
from backend.services.ingestion_service import ingestion_service
from backend.services.security_service import verify_ingest_token


router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post("/raw", response_model=IngestionResult, dependencies=[Depends(verify_ingest_token)])
async def ingest_raw_packet(packet: RawGPSPacket):
    result = await ingestion_service.enqueue(packet)
    return IngestionResult(**result)


@router.get("/status", response_model=IngestionStatus)
async def get_ingestion_status():
    return IngestionStatus(**ingestion_service.status())

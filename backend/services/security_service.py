"""
Security Service
================
Token validation helpers for ingestion and protected operations.
"""

import os
from fastapi import Header, HTTPException
from dotenv import load_dotenv

from backend.api.schemas import RawGPSPacket
from backend.services.device_service import DeviceService


def get_ingest_api_key() -> str:
    """Read ingest token from env at runtime (safe against import order issues)."""
    load_dotenv()
    return os.getenv("INGEST_API_KEY", "hackathon-key")


async def verify_ingest_token(x_ingest_token: str = Header(default="", alias="X-Ingest-Token")) -> None:
    """Verify ingestion token for external stream endpoints."""
    ingest_api_key = get_ingest_api_key()
    if not ingest_api_key:
        return
    if x_ingest_token != ingest_api_key:
        raise HTTPException(status_code=401, detail="Invalid ingestion token")


async def verify_packet_ingest_auth(
    packet: RawGPSPacket,
    x_ingest_token: str = "",
    x_device_key: str = "",
) -> None:
    """Authorize raw packet ingestion using global token or device-scoped key."""
    ingest_api_key = get_ingest_api_key()
    if ingest_api_key and x_ingest_token and x_ingest_token == ingest_api_key:
        return

    if x_device_key:
        device_service = DeviceService()
        valid = await device_service.verify_device_api_key(packet.device_id, x_device_key)
        if valid:
            return

    if not ingest_api_key and not x_device_key:
        # Preserve existing open-ingest behavior when no auth is configured.
        return

    raise HTTPException(status_code=401, detail="Invalid ingest credentials for device")

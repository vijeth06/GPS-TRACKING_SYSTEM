"""
Security Service
================
Token validation helpers for ingestion and protected operations.
"""

import os
from fastapi import Header, HTTPException
from dotenv import load_dotenv


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

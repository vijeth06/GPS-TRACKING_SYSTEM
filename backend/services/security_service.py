"""
Security Service
================
Token validation helpers for ingestion and protected operations.
"""

import os
from fastapi import Header, HTTPException


INGEST_API_KEY = os.getenv("INGEST_API_KEY", "hackathon-key")


async def verify_ingest_token(x_ingest_token: str = Header(default="", alias="X-Ingest-Token")) -> None:
    """Verify ingestion token for external stream endpoints."""
    if not INGEST_API_KEY:
        return
    if x_ingest_token != INGEST_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid ingestion token")

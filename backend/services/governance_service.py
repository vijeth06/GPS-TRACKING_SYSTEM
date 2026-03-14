"""Data governance service for masking and export controls."""

from datetime import datetime
from typing import Dict, Any

from backend.database.connection import get_database


class GovernanceService:
    def __init__(self):
        self.db = get_database()

    async def get_settings(self) -> Dict[str, Any]:
        row = await self.db.governance_settings.find_one({"name": "default"})
        if not row:
            now = datetime.utcnow()
            row = {
                "name": "default",
                "mask_device_identifier": False,
                "mask_precision_decimals": 5,
                "export_requires_admin": True,
                "updated_by": "system",
                "updated_at": now,
            }
            await self.db.governance_settings.insert_one(row)
        return self._to_response(row)

    async def update_settings(self, payload: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        now = datetime.utcnow()
        updates = {
            "mask_device_identifier": payload.get("mask_device_identifier", False),
            "mask_precision_decimals": payload.get("mask_precision_decimals", 5),
            "export_requires_admin": payload.get("export_requires_admin", True),
            "updated_by": updated_by,
            "updated_at": now,
        }
        await self.db.governance_settings.update_one(
            {"name": "default"},
            {"$set": updates, "$setOnInsert": {"name": "default"}},
            upsert=True,
        )
        row = await self.db.governance_settings.find_one({"name": "default"})
        return self._to_response(row)

    @staticmethod
    def _to_response(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(row.get("_id", "default")),
            "mask_device_identifier": row.get("mask_device_identifier", False),
            "mask_precision_decimals": row.get("mask_precision_decimals", 5),
            "export_requires_admin": row.get("export_requires_admin", True),
            "updated_by": row.get("updated_by"),
            "updated_at": row.get("updated_at", datetime.utcnow()),
        }

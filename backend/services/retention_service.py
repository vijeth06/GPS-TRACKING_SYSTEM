"""
Retention Service
=================
Archives old operational data to archive collections.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, Any

from backend.database.connection import get_database


class RetentionService:
    def __init__(self):
        self.enabled = os.getenv("RETENTION_ENABLED", "true").lower() == "true"
        self.interval_minutes = int(os.getenv("RETENTION_INTERVAL_MINUTES", "60"))
        self.cutoff_days = int(os.getenv("RETENTION_CUTOFF_DAYS", "30"))
        self._running = False
        self._task = None
        self.last_run_at = None
        self.last_result = None

    @property
    def db(self):
        return get_database()

    async def run_once(self, cutoff_days: int = None, batch_size: int = 2000) -> Dict[str, Any]:
        now = datetime.utcnow()
        effective_cutoff_days = cutoff_days if cutoff_days is not None else self.cutoff_days
        cutoff = now - timedelta(days=effective_cutoff_days)

        gps_query = {"timestamp": {"$lt": cutoff}}
        alerts_query = {"timestamp": {"$lt": cutoff}}
        packets_query = {"created_at": {"$lt": cutoff}}

        archived_gps = await self._archive_collection("gps_locations", "gps_locations_archive", gps_query, batch_size)
        archived_alerts = await self._archive_collection("alerts", "alerts_archive", alerts_query, batch_size)
        archived_packets = await self._archive_collection("raw_packets", "raw_packets_archive", packets_query, batch_size)

        result = {
            "archived_gps": archived_gps,
            "archived_alerts": archived_alerts,
            "archived_packets": archived_packets,
            "cutoff_days": effective_cutoff_days,
            "ran_at": now,
        }
        self.last_run_at = now
        self.last_result = result
        return result

    async def _archive_collection(self, source: str, target: str, query: Dict[str, Any], batch_size: int) -> int:
        count = 0
        while True:
            docs = await self.db[source].find(query).limit(batch_size).to_list(length=batch_size)
            if not docs:
                break
            for doc in docs:
                doc["archived_at"] = datetime.utcnow()
            await self.db[target].insert_many(docs, ordered=False)
            ids = [d["_id"] for d in docs if "_id" in d]
            if ids:
                await self.db[source].delete_many({"_id": {"$in": ids}})
            count += len(docs)
            if len(docs) < batch_size:
                break
        return count

    async def start_scheduler(self) -> None:
        if not self.enabled or self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop_scheduler(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except Exception:
                pass

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.run_once()
            except Exception:
                pass
            await asyncio.sleep(max(self.interval_minutes, 1) * 60)

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "interval_minutes": self.interval_minutes,
            "cutoff_days": self.cutoff_days,
            "last_run_at": self.last_run_at,
            "last_result": self.last_result,
        }


retention_service = RetentionService()

"""
Ingestion Service
=================
Queue-based ingestion for raw GPS stream packets with dedup and validation.
"""

import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any

from backend.api.schemas import RawGPSPacket, GPSDataInput
from backend.database.connection import get_database
from backend.services.gps_service import GPSService


class IngestionService:
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self.worker_task = None
        self.processed_count = 0
        self.rejected_count = 0
        self.dedup_count = 0
        self._running = False

    @property
    def db(self):
        return get_database()

    @staticmethod
    def packet_hash(packet: RawGPSPacket) -> str:
        payload = f"{packet.device_id}|{packet.timestamp.isoformat()}|{packet.latitude:.6f}|{packet.longitude:.6f}"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()

    def validate_packet(self, packet: RawGPSPacket) -> str:
        now = datetime.utcnow()
        ts = packet.timestamp.replace(tzinfo=None)
        if ts > now + timedelta(minutes=10):
            return "timestamp_too_far_future"
        if ts < now - timedelta(days=7):
            return "timestamp_too_old"
        return "ok"

    async def enqueue(self, packet: RawGPSPacket) -> Dict[str, Any]:
        p_hash = self.packet_hash(packet)
        existing = await self.db.raw_packets.find_one({"packet_hash": p_hash})
        if existing:
            self.dedup_count += 1
            return {"accepted": True, "deduplicated": True, "reason": "duplicate", "packet_hash": p_hash}

        reason = self.validate_packet(packet)
        if reason != "ok":
            self.rejected_count += 1
            return {"accepted": False, "deduplicated": False, "reason": reason, "packet_hash": p_hash}

        await self.db.raw_packets.insert_one(
            {
                "packet_hash": p_hash,
                "payload": packet.model_dump(),
                "status": "queued",
                "created_at": datetime.utcnow(),
            }
        )
        await self.queue.put((p_hash, packet))
        return {"accepted": True, "deduplicated": False, "reason": None, "packet_hash": p_hash}

    async def start_worker(self) -> None:
        if self._running:
            return
        self._running = True
        self.worker_task = asyncio.create_task(self._worker_loop())

    async def stop_worker(self) -> None:
        self._running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except Exception:
                pass

    async def _worker_loop(self) -> None:
        gps_service = GPSService()
        while self._running:
            p_hash, packet = await self.queue.get()
            try:
                gps = GPSDataInput(
                    device_id=packet.device_id,
                    latitude=packet.latitude,
                    longitude=packet.longitude,
                    timestamp=packet.timestamp,
                    speed=packet.speed,
                    heading=packet.heading,
                    accuracy=packet.accuracy,
                )
                await gps_service.process_gps_data(gps)
                await self.db.raw_packets.update_one(
                    {"packet_hash": p_hash},
                    {"$set": {"status": "processed", "processed_at": datetime.utcnow()}},
                )
                self.processed_count += 1
            except Exception as exc:
                self.rejected_count += 1
                await self.db.raw_packets.update_one(
                    {"packet_hash": p_hash},
                    {"$set": {"status": "failed", "error": str(exc), "processed_at": datetime.utcnow()}},
                )

    def status(self) -> Dict[str, Any]:
        return {
            "queue_size": self.queue.qsize(),
            "processed_count": self.processed_count,
            "rejected_count": self.rejected_count,
            "dedup_count": self.dedup_count,
            "worker_running": self._running,
        }


ingestion_service = IngestionService()

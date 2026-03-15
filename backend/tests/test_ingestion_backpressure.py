from datetime import datetime, UTC

import pytest

from backend.api.schemas import RawGPSPacket
import backend.services.ingestion_service as ingestion_module
from backend.services.ingestion_service import IngestionService


class _FakeRawPackets:
    def __init__(self):
        self._store = {}

    async def find_one(self, query):
        return self._store.get(query.get("packet_hash"))

    async def insert_one(self, doc):
        self._store[doc["packet_hash"]] = doc
        return type("InsertOneResult", (), {"inserted_id": doc["packet_hash"]})()


class _FakeDB:
    def __init__(self):
        self.raw_packets = _FakeRawPackets()


@pytest.mark.asyncio
async def test_enqueue_rejects_when_queue_full():
    svc = IngestionService(queue_maxsize=1)
    fake_db = _FakeDB()
    original_get_database = ingestion_module.get_database
    ingestion_module.get_database = lambda: fake_db

    try:
        packet_one = RawGPSPacket(
            device_id="Q1",
            latitude=11.0,
            longitude=77.0,
            timestamp=datetime.now(UTC).replace(tzinfo=None),
            speed=20.0,
        )
        packet_two = RawGPSPacket(
            device_id="Q2",
            latitude=11.1,
            longitude=77.1,
            timestamp=datetime.now(UTC).replace(tzinfo=None),
            speed=25.0,
        )

        first = await svc.enqueue(packet_one)
        second = await svc.enqueue(packet_two)

        assert first["accepted"] is True
        assert second["accepted"] is False
        assert second["reason"] == "queue_full"
    finally:
        ingestion_module.get_database = original_get_database

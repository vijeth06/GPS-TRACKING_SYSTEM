"""Stream listener service for hackathon-day GPS feeds over TCP/UDP."""

import asyncio
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

from backend.api.schemas import RawGPSPacket
from backend.services.ingestion_service import ingestion_service


class StreamListenerService:
    def __init__(self):
        self._running = False
        self._protocol = os.getenv("STREAM_PROTOCOL", "udp").strip().lower() or "udp"
        self._host = os.getenv("STREAM_HOST", "0.0.0.0")
        self._port = int(os.getenv("STREAM_PORT", "9100"))
        self._udp_transport = None
        self._tcp_server = None

        self.received_count = 0
        self.parsed_count = 0
        self.rejected_count = 0
        self.last_packet_at: Optional[datetime] = None
        self.last_error: Optional[str] = None

    async def start(self, protocol: Optional[str] = None, host: Optional[str] = None, port: Optional[int] = None) -> Dict[str, Any]:
        if self._running:
            return self.status()

        if protocol:
            self._protocol = protocol.strip().lower()
        if host:
            self._host = host
        if port:
            self._port = int(port)

        self.last_error = None

        if self._protocol not in ["udp", "tcp"]:
            self.last_error = f"Unsupported protocol: {self._protocol}"
            return self.status()

        if self._protocol == "udp":
            loop = asyncio.get_running_loop()
            transport, _ = await loop.create_datagram_endpoint(
                lambda: _UDPProtocol(self),
                local_addr=(self._host, self._port),
            )
            self._udp_transport = transport
        else:
            self._tcp_server = await asyncio.start_server(self._handle_tcp_client, host=self._host, port=self._port)

        self._running = True
        return self.status()

    async def stop(self) -> Dict[str, Any]:
        if self._udp_transport:
            self._udp_transport.close()
            self._udp_transport = None

        if self._tcp_server:
            self._tcp_server.close()
            await self._tcp_server.wait_closed()
            self._tcp_server = None

        self._running = False
        return self.status()

    async def ingest_message(self, message: str, source: str = "stream_port") -> None:
        self.received_count += 1
        payload = self._safe_parse_json(message)
        if not payload:
            self.rejected_count += 1
            self.last_error = "Invalid JSON payload"
            return

        packet = self._normalize_packet(payload, source=source)
        if not packet:
            self.rejected_count += 1
            self.last_error = "Missing required fields"
            return

        result = await ingestion_service.enqueue(packet)
        if result.get("accepted"):
            self.parsed_count += 1
            self.last_packet_at = datetime.utcnow()
        else:
            self.rejected_count += 1
            self.last_error = result.get("reason") or "Packet rejected"

    async def _handle_tcp_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="ignore").strip()
                if not text:
                    continue
                await self.ingest_message(text, source="stream_tcp")
        except Exception as exc:
            self.last_error = str(exc)
        finally:
            writer.close()
            await writer.wait_closed()

    def status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "protocol": self._protocol,
            "host": self._host,
            "port": self._port,
            "received_count": self.received_count,
            "parsed_count": self.parsed_count,
            "rejected_count": self.rejected_count,
            "last_packet_at": self.last_packet_at,
            "last_error": self.last_error,
        }

    @staticmethod
    def _safe_parse_json(raw: str) -> Optional[Dict[str, Any]]:
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    @staticmethod
    def _normalize_packet(payload: Dict[str, Any], source: str) -> Optional[RawGPSPacket]:
        device_id = payload.get("device_id") or payload.get("id") or payload.get("device")
        latitude = payload.get("latitude", payload.get("lat"))
        longitude = payload.get("longitude", payload.get("lng", payload.get("lon")))
        timestamp = payload.get("timestamp") or payload.get("ts") or datetime.utcnow().isoformat()

        if device_id is None or latitude is None or longitude is None:
            return None

        try:
            return RawGPSPacket(
                device_id=str(device_id),
                latitude=float(latitude),
                longitude=float(longitude),
                timestamp=timestamp,
                speed=float(payload["speed"]) if payload.get("speed") is not None else None,
                heading=float(payload["heading"]) if payload.get("heading") is not None else None,
                accuracy=float(payload["accuracy"]) if payload.get("accuracy") is not None else None,
                source=payload.get("source") or source,
            )
        except Exception:
            return None


class _UDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, service: StreamListenerService):
        self.service = service

    def datagram_received(self, data: bytes, addr):
        text = data.decode("utf-8", errors="ignore").strip()
        if not text:
            return
        asyncio.create_task(self.service.ingest_message(text, source="stream_udp"))


stream_listener_service = StreamListenerService()

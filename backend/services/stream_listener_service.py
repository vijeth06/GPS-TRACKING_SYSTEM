"""Stream listener service for hackathon-day GPS feeds over TCP/UDP."""

import asyncio
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import re

from backend.api.schemas import RawGPSPacket
from backend.services.ingestion_service import ingestion_service


class StreamListenerService:
    def __init__(self):
        self._running = False
        self._protocol = os.getenv("STREAM_PROTOCOL", "udp").strip().lower() or "udp"
        self._host = os.getenv("STREAM_HOST", "0.0.0.0")
        self._port = int(os.getenv("STREAM_PORT", "9100"))
        self._default_device_id = os.getenv("STREAM_DEFAULT_DEVICE_ID", "gpsfeed_device")
        self._dataset_profile = (os.getenv("STREAM_DATASET_PROFILE", "flexible") or "flexible").strip().lower()
        self._udp_transport = None
        self._tcp_server = None

        self.received_count = 0
        self.parsed_count = 0
        self.rejected_count = 0
        self.last_packet_at: Optional[datetime] = None
        self.last_error: Optional[str] = None

    async def start(
        self,
        protocol: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        dataset_profile: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self._running:
            return self.status()

        if protocol:
            self._protocol = protocol.strip().lower()
        if host:
            self._host = host
        if port:
            self._port = int(port)
        if dataset_profile:
            profile = dataset_profile.strip().lower()
            if profile in ["strict", "flexible", "vendor_x"]:
                self._dataset_profile = profile

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
        payload = None
        raw_json = self._safe_parse_json(message)
        if raw_json:
            payload = self._normalize_json_payload(
                raw_json,
                self._default_device_id,
                self._dataset_profile,
            )
        if not payload:
            payload = self._parse_nmea(message, self._default_device_id)
        if not payload:
            self.rejected_count += 1
            self.last_error = f"Unrecognised format: {message[:60]!r}"
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
            "dataset_profile": self._dataset_profile,
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
    def _pick(obj: Dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in obj and obj[key] is not None:
                return obj[key]
        return None

    @staticmethod
    def _to_iso_timestamp(value: Any) -> str:
        """Normalize timestamps (ISO string or epoch seconds/millis) to ISO-8601 string."""
        if value is None:
            return datetime.utcnow().isoformat()

        if isinstance(value, (int, float)):
            epoch = float(value)
            if epoch > 1e12:
                epoch = epoch / 1000.0
            return datetime.utcfromtimestamp(epoch).isoformat()

        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return datetime.utcnow().isoformat()
            if re.fullmatch(r"\d+(\.\d+)?", raw):
                num = float(raw)
                if num > 1e12:
                    num = num / 1000.0
                return datetime.utcfromtimestamp(num).isoformat()
            return raw

        return datetime.utcnow().isoformat()

    @classmethod
    def _extract_coordinates(cls, payload: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
        lat = cls._pick(payload, "latitude", "lat")
        lon = cls._pick(payload, "longitude", "lng", "lon", "long")

        if lat is not None and lon is not None:
            return float(lat), float(lon)

        location = payload.get("location") if isinstance(payload.get("location"), dict) else None
        if location:
            lat = cls._pick(location, "latitude", "lat")
            lon = cls._pick(location, "longitude", "lng", "lon", "long")
            if lat is not None and lon is not None:
                return float(lat), float(lon)

        coords = payload.get("coordinates") or payload.get("coords")
        if isinstance(coords, list) and len(coords) >= 2:
            a = float(coords[0])
            b = float(coords[1])
            if abs(a) <= 180 and abs(b) <= 90:
                return b, a
            if abs(a) <= 90 and abs(b) <= 180:
                return a, b

        return None, None

    @classmethod
    def _normalize_json_payload(
        cls,
        payload: Dict[str, Any],
        default_device_id: str,
        profile: str = "flexible",
    ) -> Optional[Dict[str, Any]]:
        """Normalize diverse realtime JSON datasets to the canonical packet shape."""
        profile = (profile or "flexible").strip().lower()

        if profile == "strict":
            device = cls._pick(payload, "device_id", "id", "device")
            lat = cls._pick(payload, "latitude", "lat")
            lon = cls._pick(payload, "longitude", "lng", "lon")
            if device is None or lat is None or lon is None:
                return None
            return {
                "device_id": str(device),
                "latitude": float(lat),
                "longitude": float(lon),
                "timestamp": cls._to_iso_timestamp(cls._pick(payload, "timestamp", "ts")),
                "speed": float(payload["speed"]) if payload.get("speed") is not None else None,
                "heading": float(payload["heading"]) if payload.get("heading") is not None else None,
                "accuracy": float(payload["accuracy"]) if payload.get("accuracy") is not None else None,
                "altitude": float(payload["altitude"]) if payload.get("altitude") is not None else None,
                "source": cls._pick(payload, "source") or "json_strict",
            }

        if profile == "vendor_x":
            device = cls._pick(payload, "devId", "deviceId", "imei", "tracker")
            lat = cls._pick(payload, "gpsLat", "lat", "latitude")
            lon = cls._pick(payload, "gpsLon", "lng", "lon", "longitude")
            if device is None or lat is None or lon is None:
                return None

            speed = cls._pick(payload, "spd", "speed", "speedKmh")
            if speed is None and cls._pick(payload, "speedMph") is not None:
                speed = float(cls._pick(payload, "speedMph")) * 1.60934

            heading = cls._pick(payload, "brg", "bearing", "heading")
            timestamp = cls._pick(payload, "timeMs", "time", "timestamp")
            accuracy_val = cls._pick(payload, "hdop", "accuracy")
            altitude_val = cls._pick(payload, "alt", "altitude")

            return {
                "device_id": str(device),
                "latitude": float(lat),
                "longitude": float(lon),
                "timestamp": cls._to_iso_timestamp(timestamp),
                "speed": float(speed) if speed is not None else None,
                "heading": float(heading) if heading is not None else None,
                "accuracy": float(accuracy_val) if accuracy_val is not None else None,
                "altitude": float(altitude_val) if altitude_val is not None else None,
                "source": cls._pick(payload, "source") or "json_vendor_x",
            }

        obj = payload

        for key in ("data", "payload", "gps", "position"):
            wrapped = obj.get(key)
            if isinstance(wrapped, dict):
                obj = wrapped
                break

        device = cls._pick(
            obj,
            "device_id",
            "id",
            "device",
            "imei",
            "tracker_id",
            "asset_id",
            "unit_id",
        )
        if isinstance(device, dict):
            device = cls._pick(device, "id", "device_id", "imei")
        if device is None:
            meta = obj.get("meta") if isinstance(obj.get("meta"), dict) else {}
            device = cls._pick(meta, "device_id", "id", "imei")

        lat, lon = cls._extract_coordinates(obj)
        if lat is None or lon is None:
            return None

        speed = cls._pick(obj, "speed", "speed_kmh", "velocity")
        if speed is None:
            speed_mph = cls._pick(obj, "speed_mph", "mph")
            speed_knots = cls._pick(obj, "speed_knots", "knots")
            if speed_mph is not None:
                speed = float(speed_mph) * 1.60934
            elif speed_knots is not None:
                speed = float(speed_knots) * 1.852

        heading = cls._pick(obj, "heading", "bearing", "course", "track")
        accuracy = cls._pick(obj, "accuracy", "hdop", "h_accuracy", "horizontal_accuracy")
        altitude = cls._pick(obj, "altitude", "alt", "elevation")
        ts_raw = cls._pick(obj, "timestamp", "ts", "time", "datetime", "recorded_at", "gps_time")

        return {
            "device_id": str(device or default_device_id),
            "latitude": float(lat),
            "longitude": float(lon),
            "timestamp": cls._to_iso_timestamp(ts_raw),
            "speed": float(speed) if speed is not None else None,
            "heading": float(heading) if heading is not None else None,
            "accuracy": float(accuracy) if accuracy is not None else None,
            "altitude": float(altitude) if altitude is not None else None,
            "source": cls._pick(obj, "source", "provider", "origin") or "json_stream",
        }

    @staticmethod
    def _nmea_lat_lon(value_str: str, direction: str) -> float:
        """Convert NMEA ddmm.mmmm / dddmm.mmmm to decimal degrees."""
        value = float(value_str)
        degrees = int(value / 100)
        minutes = value - degrees * 100
        decimal = degrees + minutes / 60.0
        if direction in ("S", "W"):
            decimal = -decimal
        return decimal

    @classmethod
    def _parse_nmea(cls, raw: str, default_device_id: str) -> Optional[Dict[str, Any]]:
        """
        Parse NMEA 0183 sentences from GPSFeed+.
                Supports:
                    $GPRMC / $GNRMC — recommended minimum (lat/lon/speed/heading/time)
                    $GPGGA / $GNGGA — fix data (lat/lon/altitude/accuracy)
        GPSFeed+ may optionally prepend a device-id prefix:
          "TRK101,$GPRMC,..." or "$GPRMC,..." (uses STREAM_DEFAULT_DEVICE_ID)
        """
        raw = raw.strip()
        raw = re.sub(r'\*[0-9A-Fa-f]{2}$', '', raw)

        device_id = default_device_id
        match = re.match(r'^([^$,]+),(\$.+)$', raw)
        if match:
            device_id = match.group(1).strip()
            raw = match.group(2).strip()

        if not raw.startswith('$'):
            return None

        parts = raw.split(',')
        sentence_type = parts[0].upper()

        try:
            if sentence_type in ('$GPRMC', '$GNRMC'):
                if len(parts) < 9:
                    return None
                if parts[2] != 'A':  # 'V' = void/invalid fix
                    return None
                lat = cls._nmea_lat_lon(parts[3], parts[4])
                lon = cls._nmea_lat_lon(parts[5], parts[6])
                speed_kmh = float(parts[7]) * 1.852 if parts[7] else None
                heading = float(parts[8]) if parts[8] else None
                time_str = parts[1]   # hhmmss.ss
                date_str = parts[9] if len(parts) > 9 and parts[9] else None
                if date_str:
                    ts = datetime.strptime(date_str + time_str[:6], "%d%m%y%H%M%S").isoformat()
                else:
                    ts = datetime.utcnow().isoformat()
                return {
                    "device_id": device_id,
                    "latitude": lat,
                    "longitude": lon,
                    "speed": speed_kmh,
                    "heading": heading,
                    "timestamp": ts,
                    "source": "nmea_gprmc",
                }

            elif sentence_type in ('$GPGGA', '$GNGGA'):
                if len(parts) < 10:
                    return None
                if parts[6] == '0':  # fix quality 0 = no fix
                    return None
                lat = cls._nmea_lat_lon(parts[2], parts[3])
                lon = cls._nmea_lat_lon(parts[4], parts[5])
                altitude = float(parts[9]) if parts[9] else None
                hdop = float(parts[8]) if parts[8] else None  # used as accuracy estimate
                ts = datetime.utcnow().isoformat()
                return {
                    "device_id": device_id,
                    "latitude": lat,
                    "longitude": lon,
                    "altitude": altitude,
                    "accuracy": hdop,
                    "timestamp": ts,
                    "source": "nmea_gpgga",
                }
        except (ValueError, IndexError):
            return None

        return None  # unsupported sentence type

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
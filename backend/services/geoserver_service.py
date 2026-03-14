"""
Geoserver Service
=================
Sync WFS geofence layers and expose WMS/WFS metadata.
"""

import os
from datetime import datetime
from typing import List, Dict, Any

import httpx

from backend.database.connection import get_database


class GeoserverService:
    def __init__(self):
        self.db = get_database()
        self.wfs_url = os.getenv("GEOSERVER_WFS_URL", "")
        self.wms_url = os.getenv("GEOSERVER_WMS_URL", "")
        self.layers = [l.strip() for l in os.getenv("GEOSERVER_LAYER_NAMES", "").split(",") if l.strip()]

    async def _get_layer_names(self) -> List[str]:
        config = await self.db.geoserver_config.find_one({"_id": "runtime"})
        if config and isinstance(config.get("layer_names"), list):
            return [str(l).strip() for l in config.get("layer_names", []) if str(l).strip()]
        return self.layers

    async def config_status(self) -> Dict[str, Any]:
        config = await self.db.geoserver_config.find_one({"_id": "runtime"})
        layer_names = await self._get_layer_names()
        reachable = None
        if self.wfs_url:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(self.wfs_url, params={"service": "WFS", "request": "GetCapabilities"})
                    reachable = resp.status_code < 400
            except Exception:
                reachable = False

        return {
            "wfs_url": self.wfs_url or None,
            "wms_url": self.wms_url or None,
            "layer_names": layer_names,
            "has_runtime_override": bool(config),
            "wfs_reachable": reachable,
        }

    async def update_layer_names(self, layer_names: List[str]) -> Dict[str, Any]:
        cleaned = [str(l).strip() for l in layer_names if str(l).strip()]
        await self.db.geoserver_config.update_one(
            {"_id": "runtime"},
            {
                "$set": {
                    "layer_names": cleaned,
                    "updated_at": datetime.utcnow(),
                },
                "$setOnInsert": {"created_at": datetime.utcnow()},
            },
            upsert=True,
        )
        return await self.config_status()

    async def clear_layer_cache(self) -> Dict[str, Any]:
        result = await self.db.layer_cache.delete_many({})
        return {"deleted": result.deleted_count}

    async def list_layers(self) -> List[Dict[str, Any]]:
        layer_names = await self._get_layer_names()
        out = []
        for layer in layer_names:
            cache = await self.db.layer_cache.find_one({"layer_name": layer})
            out.append(
                {
                    "layer_name": layer,
                    "wfs_enabled": bool(self.wfs_url),
                    "wms_enabled": bool(self.wms_url),
                    "last_synced_at": cache.get("last_synced_at") if cache else None,
                    "feature_count": cache.get("feature_count", 0) if cache else 0,
                }
            )
        return out

    async def sync_layers_to_geofences(self) -> Dict[str, Any]:
        imported = 0
        total_features = 0

        layer_names = await self._get_layer_names()
        if not self.wfs_url or not layer_names:
            return {"layers": await self.list_layers(), "total_features_imported": 0, "imported_geofences": 0}

        async with httpx.AsyncClient(timeout=30) as client:
            for layer in layer_names:
                params = {
                    "service": "WFS",
                    "version": "1.1.0",
                    "request": "GetFeature",
                    "typeName": layer,
                    "outputFormat": "application/json",
                }
                resp = await client.get(self.wfs_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                features = data.get("features", [])
                total_features += len(features)

                for feature in features:
                    geometry = feature.get("geometry")
                    if not geometry or geometry.get("type") not in ["Polygon", "MultiPolygon"]:
                        continue
                    properties = feature.get("properties", {})
                    name = properties.get("name") or properties.get("zone_name") or f"{layer}-zone"
                    geofence_doc = {
                        "name": name,
                        "description": f"Synced from GeoServer layer {layer}",
                        "fence_type": properties.get("zone_type", "restricted"),
                        "geometry": geometry,
                        "coordinates": [],
                        "is_active": True,
                        "source": "geoserver",
                        "source_layer": layer,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }
                    await self.db.geofences.update_one(
                        {"name": name, "source_layer": layer},
                        {"$set": geofence_doc},
                        upsert=True,
                    )
                    imported += 1

                await self.db.layer_cache.update_one(
                    {"layer_name": layer},
                    {
                        "$set": {
                            "layer_name": layer,
                            "feature_count": len(features),
                            "last_synced_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow(),
                        },
                        "$setOnInsert": {"created_at": datetime.utcnow()},
                    },
                    upsert=True,
                )

        return {
            "layers": await self.list_layers(),
            "total_features_imported": total_features,
            "imported_geofences": imported,
        }

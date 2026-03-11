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

    async def list_layers(self) -> List[Dict[str, Any]]:
        out = []
        for layer in self.layers:
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

        if not self.wfs_url or not self.layers:
            return {"layers": await self.list_layers(), "total_features_imported": 0, "imported_geofences": 0}

        async with httpx.AsyncClient(timeout=30) as client:
            for layer in self.layers:
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

"""Seed realistic prototype data across GPS tracking collections.

Usage:
  python -m backend.scripts.seed_prototype_data
  python -m backend.scripts.seed_prototype_data --seed-tag jury_batch_1 --reset-tag
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
from random import Random
from typing import Dict, List, Tuple

from backend.database.connection import init_db, close_db, get_database
from backend.services.auth_service import AuthService, UserRole


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _point(lng: float, lat: float) -> Dict[str, object]:
    return {"type": "Point", "coordinates": [lng, lat]}


def _polygon(coords: List[Tuple[float, float]]) -> Dict[str, object]:
    ring = [[lng, lat] for lat, lng in coords]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [ring]}


def _device_catalog(seed_tag: str):
    return [
        {"device_id": f"JURY_TRK_{i:03d}", "device_name": name, "device_type": dtype}
        for i, (name, dtype) in enumerate(
            [
                ("City Delivery Alpha", "vehicle"),
                ("City Delivery Beta", "vehicle"),
                ("Industrial Van", "asset"),
                ("Highway Express", "vehicle"),
                ("Field Agent", "person"),
                ("Drone Patrol", "drone"),
            ],
            start=1,
        )
    ]


def _routes_for_device(device_id: str, base_lat: float, base_lng: float) -> List[Dict[str, float]]:
    return [
        {"lat": base_lat + 0.0000, "lng": base_lng + 0.0000, "sequence": 1},
        {"lat": base_lat + 0.0040, "lng": base_lng + 0.0050, "sequence": 2},
        {"lat": base_lat + 0.0080, "lng": base_lng + 0.0100, "sequence": 3},
        {"lat": base_lat + 0.0060, "lng": base_lng + 0.0140, "sequence": 4},
        {"lat": base_lat + 0.0020, "lng": base_lng + 0.0080, "sequence": 5},
    ]


async def _delete_existing_by_tag(db, seed_tag: str) -> None:
    tagged_collections = [
        "devices",
        "gps_locations",
        "geofences",
        "alerts",
        "raw_packets",
        "alert_rule_state",
        "audit_logs",
        "trips",
        "layer_cache",
        "gps_locations_archive",
        "alerts_archive",
        "raw_packets_archive",
        "notification_channels",
        "notification_events",
        "rule_engine_rules",
        "route_plans",
        "route_deviation_events",
        "teams",
        "anomaly_insights",
    ]

    for name in tagged_collections:
        await db[name].delete_many({"seed_tag": seed_tag})

    await db.users.delete_many({"seed_tag": seed_tag})


async def seed(seed_tag: str, reset_tag: bool) -> Dict[str, int]:
    db = get_database()
    now = _utcnow_naive()
    rng = Random(42)

    if reset_tag:
        await _delete_existing_by_tag(db, seed_tag)

    counts: Dict[str, int] = {}

    users = [
        {
            "username": f"{seed_tag}_admin",
            "full_name": "Prototype Admin",
            "role": UserRole.ADMIN,
            "is_active": True,
            **AuthService.hash_password("Admin@123"),
            "created_at": now,
            "updated_at": now,
            "seed_tag": seed_tag,
        },
        {
            "username": f"{seed_tag}_ops",
            "full_name": "Prototype Operator",
            "role": UserRole.OPERATOR,
            "is_active": True,
            **AuthService.hash_password("Operator@123"),
            "created_at": now,
            "updated_at": now,
            "seed_tag": seed_tag,
        },
        {
            "username": f"{seed_tag}_viewer",
            "full_name": "Prototype Viewer",
            "role": UserRole.VIEWER,
            "is_active": True,
            **AuthService.hash_password("Viewer@123"),
            "created_at": now,
            "updated_at": now,
            "seed_tag": seed_tag,
        },
    ]
    for user in users:
        await db.users.update_one(
            {"username": user["username"]},
            {"$set": user},
            upsert=True,
        )
    counts["users"] = len(users)

    devices = _device_catalog(seed_tag)
    for idx, d in enumerate(devices):
        credential_hash = AuthService.hash_password(f"{d['device_id']}_key")
        await db.devices.update_one(
            {"device_id": d["device_id"]},
            {
                "$set": {
                    **d,
                    "status": "active",
                    **{
                        "credential_active": True,
                        "credential_rotated_at": now - timedelta(hours=idx),
                        "credential_hash": credential_hash["password_hash"],
                        "credential_salt": credential_hash["password_salt"],
                    },
                    "updated_at": now,
                    "seed_tag": seed_tag,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
    counts["devices"] = len(devices)

    geofences = [
        {
            "name": f"{seed_tag}_Warehouse_Restricted",
            "description": "High-security warehouse perimeter",
            "fence_type": "restricted",
            "is_active": True,
            "coordinates": [
                {"lat": 11.2700, "lng": 77.6000},
                {"lat": 11.2750, "lng": 77.6050},
                {"lat": 11.2800, "lng": 77.6000},
                {"lat": 11.2750, "lng": 77.5950},
            ],
        },
        {
            "name": f"{seed_tag}_Office_Allowed",
            "description": "Corporate office safe zone",
            "fence_type": "allowed",
            "is_active": True,
            "coordinates": [
                {"lat": 11.0150, "lng": 76.9500},
                {"lat": 11.0200, "lng": 76.9550},
                {"lat": 11.0180, "lng": 76.9620},
                {"lat": 11.0120, "lng": 76.9580},
            ],
        },
        {
            "name": f"{seed_tag}_School_Warning",
            "description": "School zone speed caution",
            "fence_type": "warning",
            "is_active": True,
            "coordinates": [
                {"lat": 11.0300, "lng": 76.9400},
                {"lat": 11.0340, "lng": 76.9460},
                {"lat": 11.0280, "lng": 76.9520},
            ],
        },
    ]
    for gf in geofences:
        geometry = _polygon([(x["lat"], x["lng"]) for x in gf["coordinates"]])
        await db.geofences.update_one(
            {"name": gf["name"]},
            {
                "$set": {
                    **gf,
                    "geometry": geometry,
                    "updated_at": now,
                    "seed_tag": seed_tag,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
    counts["geofences"] = len(geofences)

    gps_docs = []
    raw_docs = []
    alerts = []
    route_plans = []
    route_events = []
    trips = []
    anomalies = []
    alert_rule_state = []
    audit_logs = []

    for i, d in enumerate(devices):
        base_lat = 11.0168 + (i * 0.003)
        base_lng = 76.9558 + (i * 0.004)

        trip_started = now - timedelta(hours=6 + i)
        trip_doc = {
            "device_id": d["device_id"],
            "status": "active" if i % 2 == 0 else "completed",
            "started_at": trip_started,
            "ended_at": None if i % 2 == 0 else trip_started + timedelta(hours=2),
            "distance_km": round(38 + i * 4.7, 2),
            "seed_tag": seed_tag,
            "created_at": trip_started,
            "updated_at": now,
        }
        trips.append(trip_doc)

        waypoint_list = _routes_for_device(d["device_id"], base_lat, base_lng)
        route_plans.append(
            {
                "route_name": f"{d['device_id']}_Ops_Route",
                "device_id": d["device_id"],
                "deviation_threshold_m": 250,
                "active": True,
                "waypoints": waypoint_list,
                "created_at": now - timedelta(days=2),
                "updated_at": now,
                "seed_tag": seed_tag,
            }
        )

        for p in range(240):
            ts = now - timedelta(minutes=(240 - p))
            lat = base_lat + (0.010 * (p / 240.0)) + rng.uniform(-0.0007, 0.0007)
            lng = base_lng + (0.011 * (p / 240.0)) + rng.uniform(-0.0007, 0.0007)
            speed = max(0.0, min(95.0, 28 + 12 * (p % 12) / 11 + rng.uniform(-6, 6)))
            heading = float((p * 11 + i * 17) % 360)
            gps_docs.append(
                {
                    "device_id": d["device_id"],
                    "location": _point(lng, lat),
                    "latitude": round(lat, 6),
                    "longitude": round(lng, 6),
                    "altitude": round(380 + rng.uniform(-30, 40), 2),
                    "speed": round(speed, 2),
                    "heading": round(heading, 2),
                    "accuracy": round(rng.uniform(3.0, 18.0), 2),
                    "timestamp": ts,
                    "created_at": ts,
                    "seed_tag": seed_tag,
                }
            )
            raw_docs.append(
                {
                    "packet_hash": f"{seed_tag}:{d['device_id']}:{p}",
                    "payload": {
                        "device_id": d["device_id"],
                        "latitude": round(lat, 6),
                        "longitude": round(lng, 6),
                        "timestamp": ts.isoformat(),
                        "speed": round(speed, 2),
                        "source": "prototype_seed",
                    },
                    "status": "processed" if p % 18 else "failed",
                    "error": "simulated_noise_drop" if p % 18 == 0 else None,
                    "created_at": ts,
                    "processed_at": ts + timedelta(seconds=2),
                    "seed_tag": seed_tag,
                }
            )

        alerts.extend(
            [
                {
                    "device_id": d["device_id"],
                    "alert_type": "speed_alert",
                    "severity": "high" if i % 2 == 0 else "medium",
                    "message": f"{d['device_id']} exceeded speed threshold",
                    "purpose": "speed_compliance",
                    "latitude": base_lat + 0.01,
                    "longitude": base_lng + 0.01,
                    "location": _point(base_lng + 0.01, base_lat + 0.01),
                    "metadata": {"threshold": 80, "observed": 92 + i},
                    "status": "triggered" if i % 2 == 0 else "resolved",
                    "is_acknowledged": i % 2 != 0,
                    "acknowledged_at": now - timedelta(minutes=30) if i % 2 != 0 else None,
                    "resolved_at": now - timedelta(minutes=10) if i % 2 != 0 else None,
                    "assigned_to": f"{seed_tag}_ops",
                    "assigned_by": f"{seed_tag}_admin",
                    "assigned_at": now - timedelta(minutes=40),
                    "escalation_level": 1 if i % 2 == 0 else 0,
                    "escalated_at": now - timedelta(minutes=20) if i % 2 == 0 else None,
                    "escalation_due_at": now + timedelta(minutes=45),
                    "timestamp": now - timedelta(minutes=55),
                    "created_at": now - timedelta(minutes=55),
                    "seed_tag": seed_tag,
                },
                {
                    "device_id": d["device_id"],
                    "alert_type": "stationary_alert",
                    "severity": "medium",
                    "message": f"{d['device_id']} stationary beyond expected window",
                    "purpose": "idle_monitoring",
                    "latitude": base_lat + 0.003,
                    "longitude": base_lng + 0.004,
                    "location": _point(base_lng + 0.004, base_lat + 0.003),
                    "metadata": {"stationary_minutes": 18 + i},
                    "status": "acknowledged",
                    "is_acknowledged": True,
                    "acknowledged_at": now - timedelta(minutes=15),
                    "resolved_at": None,
                    "assigned_to": f"{seed_tag}_ops",
                    "assigned_by": f"{seed_tag}_admin",
                    "assigned_at": now - timedelta(minutes=22),
                    "escalation_level": 0,
                    "escalated_at": None,
                    "escalation_due_at": now + timedelta(minutes=20),
                    "timestamp": now - timedelta(minutes=25),
                    "created_at": now - timedelta(minutes=25),
                    "seed_tag": seed_tag,
                },
            ]
        )

        route_events.append(
            {
                "route_id": f"{seed_tag}:{d['device_id']}:route",
                "device_id": d["device_id"],
                "distance_m": round(310 + i * 18.5, 2),
                "threshold_m": 250,
                "latitude": base_lat + 0.012,
                "longitude": base_lng + 0.014,
                "timestamp": now - timedelta(minutes=35),
                "created_at": now - timedelta(minutes=35),
                "seed_tag": seed_tag,
            }
        )

        anomalies.append(
            {
                "device_id": d["device_id"],
                "anomaly_score": round(0.52 + 0.06 * (i % 4), 3),
                "reason": "Speed variability exceeds expected baseline",
                "measured_at": now - timedelta(minutes=12 + i),
                "created_at": now - timedelta(minutes=12 + i),
                "seed_tag": seed_tag,
            }
        )

        alert_rule_state.append(
            {
                "key": f"{d['device_id']}:speed_alert:{seed_tag}",
                "device_id": d["device_id"],
                "alert_type": "speed_alert",
                "last_emitted_at": now - timedelta(minutes=9 + i),
                "updated_at": now,
                "seed_tag": seed_tag,
            }
        )

        audit_logs.append(
            {
                "entity_type": "alert",
                "entity_id": f"{seed_tag}:{d['device_id']}:alert",
                "action": "assigned",
                "assigned_to": f"{seed_tag}_ops",
                "assigned_by": f"{seed_tag}_admin",
                "note": "Prototype assignment flow",
                "created_at": now - timedelta(minutes=40),
                "seed_tag": seed_tag,
            }
        )

    if gps_docs:
        await db.gps_locations.insert_many(gps_docs, ordered=False)
    if raw_docs:
        await db.raw_packets.insert_many(raw_docs, ordered=False)
    if alerts:
        await db.alerts.insert_many(alerts, ordered=False)
    if route_plans:
        await db.route_plans.insert_many(route_plans, ordered=False)
    if route_events:
        await db.route_deviation_events.insert_many(route_events, ordered=False)
    if trips:
        await db.trips.insert_many(trips, ordered=False)
    if anomalies:
        await db.anomaly_insights.insert_many(anomalies, ordered=False)
    if alert_rule_state:
        await db.alert_rule_state.insert_many(alert_rule_state, ordered=False)
    if audit_logs:
        await db.audit_logs.insert_many(audit_logs, ordered=False)

    counts["gps_locations"] = len(gps_docs)
    counts["raw_packets"] = len(raw_docs)
    counts["alerts"] = len(alerts)
    counts["route_plans"] = len(route_plans)
    counts["route_deviation_events"] = len(route_events)
    counts["trips"] = len(trips)
    counts["anomaly_insights"] = len(anomalies)
    counts["alert_rule_state"] = len(alert_rule_state)
    counts["audit_logs"] = len(audit_logs)

    channels = [
        {
            "channel_type": "in_app",
            "name": f"{seed_tag}_InApp",
            "enabled": True,
            "recipient": "operations_dashboard",
            "webhook_url": None,
            "severity_filter": ["medium", "high", "critical"],
            "created_at": now,
            "updated_at": now,
            "seed_tag": seed_tag,
        },
        {
            "channel_type": "email",
            "name": f"{seed_tag}_Email",
            "enabled": True,
            "recipient": "ops@example.com",
            "webhook_url": None,
            "severity_filter": ["high", "critical"],
            "created_at": now,
            "updated_at": now,
            "seed_tag": seed_tag,
        },
    ]
    for channel in channels:
        await db.notification_channels.update_one(
            {"channel_type": channel["channel_type"], "name": channel["name"]},
            {"$set": channel},
            upsert=True,
        )
    counts["notification_channels"] = len(channels)

    notification_events = [
        {
            "channel_id": f"{seed_tag}:in_app",
            "channel_name": f"{seed_tag}_InApp",
            "provider": "in_app",
            "severity": "high",
            "message": "Prototype alert dispatch event",
            "delivered": True,
            "details": "Stored as in-app event",
            "metadata": {"seed": True},
            "created_at": now - timedelta(minutes=5),
            "seed_tag": seed_tag,
        }
        for _ in range(8)
    ]
    await db.notification_events.insert_many(notification_events, ordered=False)
    counts["notification_events"] = len(notification_events)

    rules = [
        {
            "name": f"{seed_tag}_Escalate_Anomaly",
            "description": "Escalate anomalies above threshold",
            "event_type": "gps_point",
            "enabled": True,
            "priority": 10,
            "conditions": [{"field": "anomaly_score", "op": "gt", "value": "0.8"}],
            "actions": [{"action_type": "notify", "target": f"{seed_tag}_InApp", "payload": {"mode": "instant"}}],
            "created_at": now,
            "updated_at": now,
            "seed_tag": seed_tag,
        },
        {
            "name": f"{seed_tag}_Route_Deviation_Case",
            "description": "Open route deviation investigation",
            "event_type": "gps_point",
            "enabled": True,
            "priority": 20,
            "conditions": [{"field": "route_deviation_m", "op": "gt", "value": "250"}],
            "actions": [{"action_type": "create_incident", "target": "incident_workspace", "payload": {"priority": "high"}}],
            "created_at": now,
            "updated_at": now,
            "seed_tag": seed_tag,
        },
    ]
    await db.rule_engine_rules.insert_many(rules, ordered=False)
    counts["rule_engine_rules"] = len(rules)

    teams = [
        {
            "team_name": f"{seed_tag}_OpsAlpha",
            "lead_username": f"{seed_tag}_ops",
            "members": [f"{seed_tag}_admin", f"{seed_tag}_ops"],
            "on_call": True,
            "created_at": now,
            "updated_at": now,
            "seed_tag": seed_tag,
        },
        {
            "team_name": f"{seed_tag}_FieldResponse",
            "lead_username": f"{seed_tag}_admin",
            "members": [f"{seed_tag}_ops", f"{seed_tag}_viewer"],
            "on_call": False,
            "created_at": now,
            "updated_at": now,
            "seed_tag": seed_tag,
        },
    ]
    for team in teams:
        await db.teams.update_one({"team_name": team["team_name"]}, {"$set": team}, upsert=True)
    counts["teams"] = len(teams)

    await db.governance_settings.update_one(
        {"name": "default"},
        {
            "$set": {
                "name": "default",
                "mask_device_identifier": True,
                "mask_precision_decimals": 4,
                "export_requires_admin": True,
                "updated_by": f"{seed_tag}_admin",
                "updated_at": now,
                "seed_tag": seed_tag,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    counts["governance_settings"] = 1

    await db.geoserver_config.update_one(
        {"_id": "runtime"},
        {
            "$set": {
                "layer_names": ["zones_live", "zones_buffer"],
                "updated_at": now,
                "seed_tag": seed_tag,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    counts["geoserver_config"] = 1

    layer_cache = [
        {
            "layer_name": "zones_live",
            "feature_count": 24,
            "last_synced_at": now - timedelta(minutes=20),
            "updated_at": now - timedelta(minutes=20),
            "created_at": now - timedelta(days=1),
            "seed_tag": seed_tag,
        },
        {
            "layer_name": "zones_buffer",
            "feature_count": 24,
            "last_synced_at": now - timedelta(minutes=20),
            "updated_at": now - timedelta(minutes=20),
            "created_at": now - timedelta(days=1),
            "seed_tag": seed_tag,
        },
    ]
    for item in layer_cache:
        await db.layer_cache.update_one({"layer_name": item["layer_name"]}, {"$set": item}, upsert=True)
    counts["layer_cache"] = len(layer_cache)

    archive_cutoff = now - timedelta(days=60)
    gps_archive = []
    alerts_archive = []
    packets_archive = []
    for d in devices:
        for i in range(12):
            ts = archive_cutoff + timedelta(hours=i)
            lat = 11.0168 + (i * 0.0008)
            lng = 76.9558 + (i * 0.0009)
            gps_archive.append(
                {
                    "device_id": d["device_id"],
                    "location": _point(lng, lat),
                    "latitude": lat,
                    "longitude": lng,
                    "speed": round(20 + i * 1.3, 2),
                    "heading": float((i * 27) % 360),
                    "accuracy": 8.0,
                    "timestamp": ts,
                    "created_at": ts,
                    "archived_at": now - timedelta(days=5),
                    "seed_tag": seed_tag,
                }
            )
            packets_archive.append(
                {
                    "packet_hash": f"archive:{seed_tag}:{d['device_id']}:{i}",
                    "payload": {
                        "device_id": d["device_id"],
                        "latitude": lat,
                        "longitude": lng,
                        "timestamp": ts.isoformat(),
                    },
                    "status": "processed",
                    "created_at": ts,
                    "processed_at": ts + timedelta(seconds=2),
                    "archived_at": now - timedelta(days=5),
                    "seed_tag": seed_tag,
                }
            )
        alerts_archive.append(
            {
                "device_id": d["device_id"],
                "alert_type": "offline_alert",
                "severity": "low",
                "message": "Historical offline event",
                "purpose": "connectivity_monitoring",
                "metadata": {"historical": True},
                "status": "resolved",
                "is_acknowledged": True,
                "acknowledged_at": archive_cutoff + timedelta(hours=1),
                "resolved_at": archive_cutoff + timedelta(hours=2),
                "escalation_level": 0,
                "timestamp": archive_cutoff,
                "created_at": archive_cutoff,
                "archived_at": now - timedelta(days=5),
                "seed_tag": seed_tag,
            }
        )

    await db.gps_locations_archive.insert_many(gps_archive, ordered=False)
    await db.alerts_archive.insert_many(alerts_archive, ordered=False)
    await db.raw_packets_archive.insert_many(packets_archive, ordered=False)
    counts["gps_locations_archive"] = len(gps_archive)
    counts["alerts_archive"] = len(alerts_archive)
    counts["raw_packets_archive"] = len(packets_archive)

    return counts


async def _main(seed_tag: str, reset_tag: bool) -> None:
    await init_db()
    try:
        counts = await seed(seed_tag=seed_tag, reset_tag=reset_tag)
    finally:
        await close_db()

    print("Prototype seed completed")
    print(f"Seed tag: {seed_tag}")
    for key in sorted(counts.keys()):
        print(f"- {key}: {counts[key]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed realistic prototype dataset")
    parser.add_argument("--seed-tag", default="jury_prototype", help="Tag to group seeded records")
    parser.add_argument(
        "--reset-tag",
        action="store_true",
        help="Delete existing records matching the same seed tag before seeding",
    )
    args = parser.parse_args()
    asyncio.run(_main(seed_tag=args.seed_tag, reset_tag=args.reset_tag))


if __name__ == "__main__":
    main()

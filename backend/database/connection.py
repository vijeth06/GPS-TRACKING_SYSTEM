"""
Database Connection Module
==========================
Handles MongoDB database connections using Motor (async) and PyMongo.

Architecture:
    GPS Simulator → FastAPI Backend → Processing Engine → MongoDB Database
    
This module establishes the connection and provides database access
for all database operations throughout the application.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB configuration
MONGODB_URL = os.getenv(
    "MONGODB_URL",
    "mongodb+srv://vijeth:2006@wtlab.9b3zqxr.mongodb.net/Anna_Univ"
)
DATABASE_NAME = os.getenv("DATABASE_NAME", "Anna_Univ")

# Async MongoDB client (for FastAPI async operations)
async_client = None
# Sync MongoDB client (for synchronous operations)
sync_client: MongoClient = None

# Database instance
db = None


def get_database():
    """
    Get the MongoDB database instance.
    
    Returns:
        Database: MongoDB database instance
    """
    return db


def get_sync_db():
    """
    Get synchronous database for non-async operations.
    """
    if sync_client is None:
        init_sync_db()
    return sync_client[DATABASE_NAME]


def init_sync_db():
    """Initialize synchronous MongoDB client."""
    global sync_client
    sync_client = MongoClient(MONGODB_URL)


async def init_db():
    """
    Initialize MongoDB connection.
    Creates indexes for optimal query performance.
    """
    global async_client, db
    
    async_client = AsyncIOMotorClient(MONGODB_URL)
    db = async_client[DATABASE_NAME]
    
    # Create indexes for collections
    await create_indexes()
    
    print(f"Connected to MongoDB: {DATABASE_NAME}")
    return db


async def create_indexes():
    """
    Create indexes for optimal query performance.
    """
    # Devices collection indexes
    await db.devices.create_index("device_id", unique=True)
    await db.devices.create_index("status")

    # Users collection indexes
    await db.users.create_index("username", unique=True)
    await db.users.create_index("role")
    await db.users.create_index("is_active")
    
    # GPS locations collection indexes
    await db.gps_locations.create_index("device_id")
    await db.gps_locations.create_index("timestamp")
    await db.gps_locations.create_index([("device_id", 1), ("timestamp", -1)])
    # 2dsphere index for geospatial queries
    await db.gps_locations.create_index([("location", "2dsphere")])
    
    # Geofences collection indexes
    await db.geofences.create_index("is_active")
    await db.geofences.create_index([("geometry", "2dsphere")])
    
    # Alerts collection indexes
    await db.alerts.create_index("device_id")
    await db.alerts.create_index("alert_type")
    await db.alerts.create_index("is_acknowledged")
    await db.alerts.create_index("status")
    await db.alerts.create_index("timestamp")
    await db.alerts.create_index([("device_id", 1), ("timestamp", -1)])

    # Raw packet ingestion indexes
    await db.raw_packets.create_index("packet_hash", unique=True)
    await db.raw_packets.create_index("status")
    await db.raw_packets.create_index("created_at")

    # Alert rule and audit indexes
    await db.alert_rule_state.create_index("key", unique=True)
    await db.audit_logs.create_index("created_at")
    await db.audit_logs.create_index([("entity_type", 1), ("entity_id", 1)])

    # Trip intelligence indexes
    await db.trips.create_index("device_id")
    await db.trips.create_index("status")
    await db.trips.create_index([("device_id", 1), ("status", 1)])

    # GeoServer layer cache indexes
    await db.layer_cache.create_index("layer_name", unique=True)
    await db.geoserver_config.create_index("updated_at")

    # Archive collection indexes
    await db.gps_locations_archive.create_index("timestamp")
    await db.gps_locations_archive.create_index("archived_at")
    await db.alerts_archive.create_index("timestamp")
    await db.alerts_archive.create_index("archived_at")
    await db.raw_packets_archive.create_index("created_at")
    await db.raw_packets_archive.create_index("archived_at")

    # Notification indexes
    await db.notification_channels.create_index([("channel_type", 1), ("name", 1)], unique=True)
    await db.notification_events.create_index("created_at")
    await db.notification_events.create_index("provider")

    # Rule engine indexes
    await db.rule_engine_rules.create_index("event_type")
    await db.rule_engine_rules.create_index([("enabled", 1), ("priority", 1)])

    # Route management indexes
    await db.route_plans.create_index([("device_id", 1), ("active", 1)])
    await db.route_deviation_events.create_index("timestamp")
    await db.route_deviation_events.create_index("device_id")

    # Admin and governance indexes
    await db.teams.create_index("team_name", unique=True)
    await db.governance_settings.create_index("name", unique=True)

    # Intelligence indexes
    await db.anomaly_insights.create_index("device_id")
    await db.anomaly_insights.create_index("measured_at")


async def close_db():
    """
    Close MongoDB connection.
    """
    global async_client, sync_client
    
    if async_client:
        async_client.close()
        async_client = None
    
    if sync_client:
        sync_client.close()
        sync_client = None
    
    print("MongoDB connection closed")

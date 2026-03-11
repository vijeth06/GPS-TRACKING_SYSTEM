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
async_client: AsyncIOMotorClient = None
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
    await db.alerts.create_index("timestamp")
    await db.alerts.create_index([("device_id", 1), ("timestamp", -1)])


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

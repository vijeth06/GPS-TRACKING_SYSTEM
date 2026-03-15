"""
GPS Tracking System - FastAPI Main Application
==============================================

Real-Time GPS Tracking and Movement Intelligence System

Architecture:
    GPS Simulator → FastAPI Backend → Processing Engine → MongoDB Database
                                   ↓
                         WebSocket Streaming
                                   ↓
                         React Dashboard

This is the main entry point for the backend API server.
It sets up:
- FastAPI application with CORS
- Socket.IO for real-time WebSocket communication
- MongoDB database initialization
- API route registration
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
import uvicorn
from contextlib import asynccontextmanager

from backend.api.gps_routes import router as gps_router
from backend.api.alert_routes import router as alert_router
from backend.api.geofence_routes import router as geofence_router
from backend.api.analytics_routes import router as analytics_router
from backend.api.auth_routes import router as auth_router
from backend.api.ingest_routes import router as ingest_router
from backend.api.geoserver_routes import router as geoserver_router
from backend.api.ops_routes import router as ops_router
from backend.api.incident_routes import router as incident_router
from backend.api.retention_routes import router as retention_router
from backend.api.notification_routes import router as notification_router
from backend.api.rule_engine_routes import router as rule_engine_router
from backend.api.route_management_routes import router as route_management_router
from backend.api.admin_routes import router as admin_router
from backend.api.reporting_routes import router as reporting_router
from backend.api.governance_routes import router as governance_router
from backend.api.intelligence_routes import router as intelligence_router
from backend.database.connection import init_db, close_db, get_database
from backend.services.socket_manager import socket_manager
from backend.services.ingestion_service import ingestion_service
from backend.services.auth_service import AuthService
from backend.services.retention_service import retention_service
from backend.services.stream_listener_service import stream_listener_service



sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=['*'],  # Configure for production
    logger=True,
    engineio_logger=False
)

socket_manager.set_socketio(sio)


@sio.event
async def connect(sid, environ):
    """Handle client connection."""
    print(f"Client connected: {sid}")
    socket_manager.add_client(sid)
    await sio.emit('connected', {'sid': sid}, to=sid)


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    print(f"Client disconnected: {sid}")
    socket_manager.remove_client(sid)


@sio.event
async def subscribe_device(sid, data):
    """Subscribe to updates for a specific device."""
    device_id = data.get('device_id')
    if device_id:
        await sio.enter_room(sid, f"device_{device_id}")
        print(f"Client {sid} subscribed to device {device_id}")


@sio.event
async def unsubscribe_device(sid, data):
    """Unsubscribe from device updates."""
    device_id = data.get('device_id')
    if device_id:
        await sio.leave_room(sid, f"device_{device_id}")



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    print("Starting GPS Tracking System...")
    
    await init_db()
    print("MongoDB connection established")

    await AuthService().ensure_default_admin()

    await ingestion_service.start_worker()
    await retention_service.start_scheduler()

    stream_autostart = os.getenv("STREAM_AUTOSTART", "false").strip().lower() in ["1", "true", "yes", "on"]
    if stream_autostart:
        await stream_listener_service.start()
        print("Stream listener started from environment configuration")

    yield

    print("Shutting down GPS Tracking System...")
    await stream_listener_service.stop()
    await ingestion_service.stop_worker()
    await retention_service.stop_scheduler()
    await close_db()


app = FastAPI(
    title="GPS Tracking System",
    description="""
    Real-Time GPS Tracking and Movement Intelligence System
    
    
    * **Live GPS Tracking**: Receive and process GPS data from multiple devices
    * **Movement Analytics**: Speed calculation, distance tracking, stationary detection
    * **Geofence Monitoring**: Define zones and detect violations
    * **Real-time Alerts**: Instant notifications for anomalies
    * **WebSocket Updates**: Live map updates via Socket.IO
    
    
    ```
    GPS Simulator → FastAPI Backend → MongoDB Database
                         ↓
               WebSocket Streaming
                         ↓
                  React Dashboard
    ```
    """,
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gps_router, prefix="/api")
app.include_router(alert_router, prefix="/api")
app.include_router(geofence_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")
app.include_router(geoserver_router, prefix="/api")
app.include_router(ops_router, prefix="/api")
app.include_router(incident_router, prefix="/api")
app.include_router(retention_router, prefix="/api")
app.include_router(notification_router, prefix="/api")
app.include_router(rule_engine_router, prefix="/api")
app.include_router(route_management_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(reporting_router, prefix="/api")
app.include_router(governance_router, prefix="/api")
app.include_router(intelligence_router, prefix="/api")



@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - health check."""
    return {
        "service": "GPS Tracking System",
        "status": "running",
        "version": "1.0.0",
        "database": "MongoDB"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    db = get_database()
    try:
        await db.command("ping")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status
    }



socket_app = socketio.ASGIApp(sio, app)



if __name__ == "__main__":
    uvicorn.run(
        "backend.main:socket_app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
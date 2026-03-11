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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
import uvicorn
from contextlib import asynccontextmanager

from backend.api.gps_routes import router as gps_router
from backend.api.alert_routes import router as alert_router
from backend.api.geofence_routes import router as geofence_router
from backend.api.analytics_routes import router as analytics_router
from backend.database.connection import init_db, close_db, get_database
from backend.services.socket_manager import socket_manager


# =============================================================================
# SOCKET.IO SETUP
# =============================================================================

# Create Socket.IO server with async support
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=['*'],  # Configure for production
    logger=True,
    engineio_logger=False
)

# Set socket manager's sio instance
socket_manager.set_socketio(sio)


# Socket.IO event handlers
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


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    # Startup
    print("Starting GPS Tracking System...")
    
    # Initialize MongoDB connection
    await init_db()
    print("MongoDB connection established")
    
    # Initialize sample data if needed
    await init_sample_data()
    
    yield
    
    # Shutdown
    print("Shutting down GPS Tracking System...")
    await close_db()


async def init_sample_data():
    """Initialize sample data for development."""
    from backend.models.device import create_device_document
    
    db = get_database()
    try:
        # Check if devices exist
        existing = await db.devices.find_one()
        if not existing:
            # Create sample devices
            sample_devices = [
                create_device_document(device_id="TRK101", device_name="Delivery Truck 1", device_type="vehicle"),
                create_device_document(device_id="TRK102", device_name="Delivery Truck 2", device_type="vehicle"),
                create_device_document(device_id="TRK103", device_name="Service Van 1", device_type="vehicle"),
                create_device_document(device_id="TRK104", device_name="Service Van 2", device_type="vehicle"),
                create_device_document(device_id="TRK105", device_name="Executive Car", device_type="vehicle"),
            ]
            await db.devices.insert_many(sample_devices)
            print("Sample devices created")
    except Exception as e:
        print(f"Sample data initialization note: {e}")


# Create FastAPI app
app = FastAPI(
    title="GPS Tracking System",
    description="""
    Real-Time GPS Tracking and Movement Intelligence System
    
    ## Features
    
    * **Live GPS Tracking**: Receive and process GPS data from multiple devices
    * **Movement Analytics**: Speed calculation, distance tracking, stationary detection
    * **Geofence Monitoring**: Define zones and detect violations
    * **Real-time Alerts**: Instant notifications for anomalies
    * **WebSocket Updates**: Live map updates via Socket.IO
    
    ## Architecture
    
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

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(gps_router, prefix="/api")
app.include_router(alert_router, prefix="/api")
app.include_router(geofence_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")


# =============================================================================
# HEALTH CHECK ENDPOINTS
# =============================================================================

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
        # Quick MongoDB ping
        await db.command("ping")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status
    }


# =============================================================================
# SOCKET.IO APP WRAPPER
# =============================================================================

# Wrap FastAPI app with Socket.IO
socket_app = socketio.ASGIApp(sio, app)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:socket_app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "websocket_clients": socket_manager.connected_count
    }


# =============================================================================
# COMBINED ASGI APPLICATION
# =============================================================================

# Wrap FastAPI with Socket.IO
socket_app = socketio.ASGIApp(sio, app)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:socket_app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

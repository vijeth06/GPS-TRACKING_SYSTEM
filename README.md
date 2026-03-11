# Real-Time GPS Tracking and Movement Intelligence System

A comprehensive GPS tracking platform that receives continuous GPS streams, visualizes devices on a live map, stores spatial trails, performs real-time movement analytics, detects geofence violations, generates alerts, and displays insights on a dashboard.

![System Architecture](docs/architecture.png)

## 🏗️ System Architecture

```
┌─────────────────┐
│  GPS Simulator  │ ─── Generates realistic GPS data for multiple devices
└────────┬────────┘
         │ HTTP POST /api/gps
         ▼
┌─────────────────┐
│ FastAPI Backend │ ─── REST API + WebSocket server
│  + Socket.IO    │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌──────────┐ ┌──────────────────┐
│ MongoDB  │ │Processing Engine │ ─── Movement analysis, geofence detection
│ (GeoJSON)│ │  (Analytics)     │
└──────────┘ └─────────┬────────┘
                    │
                    │ WebSocket (device_location_update, alert_update)
                    ▼
          ┌─────────────────┐
          │ React Dashboard │ ─── Leaflet map, charts, alerts panel
          │   (Vite)        │
          └─────────────────┘
```

## ✨ Features

### Core Features
- **Live GPS Tracking**: Real-time device location updates on interactive map
- **Movement Trail Visualization**: View device movement history as polylines
- **Speed Analytics**: Calculate speed, detect stationary devices, classify movement
- **Geofence Detection**: Define polygons and detect zone violations
- **Alert System**: Real-time alerts for anomalies (stationary, speed, geofence)
- **Analytics Dashboard**: Charts, statistics, and insights

### Advanced Features
- **Multiple Device Support**: Track 5-10+ devices simultaneously
- **WebSocket Updates**: Instant map updates without page refresh
- **GeoJSON Spatial Queries**: Efficient geographic computations with 2dsphere indexes
- **Heatmap Data**: Frequently visited areas analysis
- **Queue-based Ingestion**: Raw stream ingestion with deduplication and validation
- **Ops Snapshot**: Live operational health metrics for monitoring
- **GeoServer Sync Hooks**: WFS/WMS layer integration endpoints

## 🛠️ Technology Stack

### Backend
- **Python 3.10+** with **FastAPI**
- **MongoDB Atlas / MongoDB 6+** with **Motor + PyMongo**
- **GeoJSON + 2dsphere indexes** for spatial processing
- **Socket.IO** for WebSockets

### Frontend
- **React 18** with **Vite**
- **Leaflet.js** for maps (via react-leaflet)
- **TailwindCSS** for styling
- **Chart.js** for analytics charts

## 📁 Project Structure

```
gps-tracking-system/
├── backend/
│   ├── main.py                 # FastAPI application entry
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example           # Environment variables template
│   ├── api/
│   │   ├── schemas.py         # Pydantic models
│   │   ├── gps_routes.py      # GPS endpoints
│   │   ├── alert_routes.py    # Alert endpoints
│   │   ├── geofence_routes.py # Geofence endpoints
│   │   └── analytics_routes.py# Analytics endpoints
│   ├── database/
│   │   ├── connection.py      # Database connection
│   │   └── schema.sql         # SQL schema with PostGIS
│   ├── models/
│   │   ├── device.py          # Device model
│   │   ├── gps_location.py    # GPS location model
│   │   ├── geofence.py        # Geofence model
│   │   └── alert.py           # Alert model
│   ├── services/
│   │   ├── gps_service.py     # GPS data processing
│   │   ├── device_service.py  # Device management
│   │   ├── alert_service.py   # Alert management
│   │   ├── geofence_service.py# Geofence operations
│   │   ├── analytics_service.py# Analytics
│   │   └── socket_manager.py  # WebSocket manager
│   └── analytics/
│       └── movement_analyzer.py# Speed, distance, patterns
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css
│       ├── services/
│       │   ├── api.js         # HTTP client
│       │   └── socket.js      # WebSocket client
│       ├── pages/
│       │   └── Dashboard.jsx  # Main dashboard
│       └── components/
│           ├── MapView.jsx    # Leaflet map
│           ├── DeviceMarker.jsx# Device markers
│           ├── TrailLayer.jsx # Movement trails
│           ├── GeofenceLayer.jsx# Geofence polygons
│           ├── DeviceList.jsx # Device list
│           ├── AlertPanel.jsx # Alerts feed
│           └── AnalyticsDashboard.jsx # Charts
│
├── simulator/
│   ├── gps_simulator.py       # Basic GPS simulator
│   └── route_simulator.py     # Advanced route-based simulator
│
└── README.md
```

## 🚀 Getting Started

### Prerequisites

1. **Python 3.10+**
2. **Node.js 18+**
3. **MongoDB Atlas connection string** (or local MongoDB)

### Step 1: Database Setup

1. Create a MongoDB Atlas cluster (or run local MongoDB).
2. Configure `backend/.env` using `backend/.env.example`:
   ```env
   MONGODB_URL=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/Anna_Univ
   DATABASE_NAME=Anna_Univ
   ```

### Step 2: Backend Setup

1. Navigate to backend directory:
   ```bash
   cd gps-tracking-system/backend
   ```

2. Create virtual environment:
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. Start the backend server:
   ```bash
   # From project root on Windows PowerShell
   $env:PYTHONPATH="d:\Anna\gps-tracking-system"
   cd backend
   python -m uvicorn main:socket_app --host 0.0.0.0 --port 8000 --reload
   ```

   The API will be available at `http://localhost:8000`
   - API docs: `http://localhost:8000/docs`

### Step 3: Frontend Setup

1. Navigate to frontend directory:
   ```bash
   cd gps-tracking-system/frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start development server:
   ```bash
   npm run dev
   ```

   The dashboard will be available at `http://localhost:5173`

### Step 4: Start GPS Simulator

1. In a new terminal, navigate to simulator:
   ```bash
   cd gps-tracking-system/simulator
   ```

2. Run the basic simulator:
   ```bash
   python gps_simulator.py
   ```

   Or run the advanced route simulator:
   ```bash
   python route_simulator.py
   ```

## 📡 API Endpoints

### GPS Data
- `POST /api/gps` - Receive GPS data from devices
- `GET /api/devices` - List all devices with locations
- `GET /api/device/{id}` - Get specific device details
- `GET /api/device/{id}/trail` - Get device movement history

### Alerts
- `GET /api/alerts` - Get alerts (with filters)
- `GET /api/alerts/unacknowledged` - Get unacknowledged alerts
- `POST /api/alerts/{id}/acknowledge` - Acknowledge an alert
- `POST /api/alerts/{id}/resolve` - Resolve an alert

### Geofences
- `GET /api/geofences` - Get all geofences
- `POST /api/geofences` - Create a geofence
- `DELETE /api/geofences/{id}` - Delete a geofence

### Analytics
- `GET /api/analytics/device/{id}` - Device analytics
- `GET /api/analytics/system` - System-wide analytics
- `GET /api/analytics/speed/{id}` - Speed over time data
- `GET /api/analytics/heatmap` - Location frequency data

### Workflow / Ops
- `GET /api/ops/snapshot` - Operational metrics snapshot
- `GET /api/ingest/status` - Ingestion worker queue status
- `POST /api/ingest/raw` - Ingest raw packet (requires `X-Ingest-Token`)
- `GET /api/geoserver/layers` - List configured GeoServer layers
- `POST /api/geoserver/sync` - Sync WFS layers to geofences
- `POST /api/demo/geofence-violation` - Seed demo geofence scenario
- `POST /api/demo/stationary?device_id=TRK101` - Seed demo stationary scenario

## 🌐 WebSocket Events

### Emitted by Server
- `device_location_update` - New GPS location received
- `alert_update` - New alert generated
- `device_status_change` - Device online/offline

### Payload Examples

```javascript
// device_location_update
{
  "device_id": "TRK101",
  "lat": 11.2754,
  "lng": 77.6072,
  "speed": 45.5,
  "status": "normal",
  "timestamp": "2026-03-10T10:01:22Z"
}

// alert_update
{
  "id": 1,
  "device_id": "TRK101",
  "alert_type": "geofence_alert",
  "severity": "high",
  "message": "Device entered restricted zone: Warehouse Zone A",
  "timestamp": "2026-03-10T10:05:30Z"
}
```

## 🎮 User Flow

1. **Start System**: Backend → Simulator → Frontend
2. **View Map**: Devices appear as colored markers
3. **Select Device**: Click marker to see trail and analytics
4. **Monitor Alerts**: Real-time alerts appear in panel
5. **View Geofences**: Colored polygons on map
6. **Analyze**: Check speed charts and statistics

## 🔧 Configuration

### Environment Variables (backend/.env)

```env
MONGODB_URL=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/Anna_Univ
DATABASE_NAME=Anna_Univ
INGEST_API_KEY=hackathon-key
GEOSERVER_WFS_URL=
GEOSERVER_WMS_URL=
GEOSERVER_LAYER_NAMES=
DEBUG=True
CORS_ORIGINS=http://localhost:5173
SPEED_VIOLATION_THRESHOLD=120
STATIONARY_TIME_THRESHOLD=300
```

### Speed Classifications

| Speed Range | Status |
|------------|--------|
| 0-5 km/h | Stationary |
| 5-20 km/h | Slow |
| 20-60 km/h | Normal |
| >60 km/h | Fast |

## 🛡️ Alert Types

| Alert Type | Trigger |
|-----------|---------|
| `stationary_alert` | Device stopped > 5 minutes |
| `speed_alert` | Speed > 120 km/h |
| `geofence_alert` | Entered restricted zone |

## 📊 Sample Geofences

The schema includes sample geofences near Coimbatore, India:
- **Warehouse Zone A** (Restricted)
- **Office Complex** (Allowed)
- **Speed Warning Zone** (Warning)

## 🔜 Future Enhancements

- [ ] Heatmap visualization
- [ ] Device playback feature
- [ ] Multi-device filtering
- [ ] Route history viewer
- [ ] Route replay UI with timeline scrubber
- [ ] GeoServer layer style controls in map UI
- [ ] Device authentication and per-device token onboarding

## 📝 License

MIT License - feel free to use for learning and projects.

## 👥 Contributing

Contributions welcome! Please read contributing guidelines first.

---

Built for hackathons and real-world GPS tracking applications.

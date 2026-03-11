# GPS Tracking System - Quick Start

## Windows Quick Start

### 1. Setup Database (PostgreSQL + PostGIS)
```powershell
# Install PostgreSQL from https://www.postgresql.org/download/windows/
# During installation, use Stack Builder to install PostGIS

# Create database
psql -U postgres
CREATE DATABASE gps_tracking;
\c gps_tracking
CREATE EXTENSION postgis;
\q
```

### 2. Start Backend
```powershell
cd gps-tracking-system\backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:socket_app --host 0.0.0.0 --port 8000 --reload
```

### 3. Start Frontend (new terminal)
```powershell
cd gps-tracking-system\frontend
npm install
npm run dev
```

### 4. Start Simulator (new terminal)
```powershell
cd gps-tracking-system\simulator
python gps_simulator.py
```

### 5. Open Dashboard
Navigate to http://localhost:5173

## Expected Result
- Map shows 5-10 devices moving
- Trails appear behind selected device
- Alerts pop up for stationary/speed/geofence violations
- Analytics update in real-time

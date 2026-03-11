# GPS Tracking System - Quick Start

## Windows Quick Start

### 1. Setup Database (MongoDB Atlas)
```powershell
# Use your MongoDB Atlas connection in backend/.env
# Example:
# MONGODB_URL=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/Anna_Univ
```

### 2. Start Backend
```powershell
cd gps-tracking-system
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
$env:PYTHONPATH="d:\Anna\gps-tracking-system"
cd backend
python -m uvicorn main:socket_app --host 0.0.0.0 --port 8000 --reload
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

### 6. Optional Workflow APIs
- `GET /api/ops/snapshot` for operational metrics
- `GET /api/ingest/status` for ingestion queue status
- `POST /api/demo/geofence-violation` to seed a demo restricted zone
- `POST /api/demo/stationary?device_id=TRK101` to seed stationary behavior

## Expected Result
- Map shows 5-10 devices moving
- Trails appear behind selected device
- Alerts pop up for stationary/speed/geofence violations
- Analytics update in real-time

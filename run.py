"""
Alternative Main Entry Point
============================
Use this file if you want to run the server with:
    python run.py
    
Instead of:
    uvicorn backend.main:socket_app --reload
"""

import uvicorn
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("=" * 60)
    print("GPS Tracking System - Starting Server")
    print("=" * 60)
    print()
    print("🚀 Starting FastAPI server...")
    print("📍 API Docs: http://localhost:8000/docs")
    print("🌐 Dashboard: http://localhost:5173 (start frontend separately)")
    print()
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    uvicorn.run(
        "backend.main:socket_app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
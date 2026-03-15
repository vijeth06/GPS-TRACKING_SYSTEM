"""
Analytics Routes
================
API endpoints for movement analytics.

Endpoints:
    GET /analytics/device/{id} - Get analytics for a device
    GET /analytics/system - Get system-wide analytics
    GET /analytics/speed - Get speed over time data
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta

from backend.api.schemas import DeviceAnalytics, SystemAnalytics, SpeedOverTime
from backend.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/device/{device_id}", response_model=DeviceAnalytics, summary="Get device analytics")
async def get_device_analytics(
    device_id: str,
    start_time: Optional[datetime] = Query(None, description="Start of time range"),
    end_time: Optional[datetime] = Query(None, description="End of time range")
):
    """
    Get analytics for a specific device.
    
    Includes:
    - Total distance traveled
    - Average and max speed
    - Stationary vs moving time
    - Current movement status
    
    Args:
        device_id: Unique device identifier
        start_time: Start of analysis period (default: last 24 hours)
        end_time: End of analysis period (default: now)
        
    Returns:
        Device analytics data
    """
    if not end_time:
        end_time = datetime.utcnow()
    if not start_time:
        start_time = end_time - timedelta(hours=24)
    
    analytics_service = AnalyticsService()
    analytics = await analytics_service.get_device_analytics(device_id, start_time, end_time)
    
    if not analytics:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    return analytics


@router.get("/system", response_model=SystemAnalytics, summary="Get system analytics")
async def get_system_analytics():
    """
    Get system-wide analytics.
    
    Includes:
    - Total and online device count
    - Alert counts
    - Total distance across all devices
    - Average speed across all devices
    
    Returns:
        System-wide analytics data
    """
    analytics_service = AnalyticsService()
    analytics = await analytics_service.get_system_analytics()
    return analytics


@router.get("/speed/{device_id}", response_model=SpeedOverTime, summary="Get speed over time")
async def get_speed_over_time(
    device_id: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    interval_minutes: int = Query(5, ge=1, le=60, description="Data point interval")
):
    """
    Get speed data over time for charting.
    
    Returns speed readings aggregated by time interval for creating
    line charts or area graphs.
    
    Args:
        device_id: Unique device identifier
        start_time: Start of time range
        end_time: End of time range
        interval_minutes: Aggregation interval in minutes
        
    Returns:
        Speed data points for charting
    """
    if not end_time:
        end_time = datetime.utcnow()
    if not start_time:
        start_time = end_time - timedelta(hours=6)
    
    analytics_service = AnalyticsService()
    speed_data = await analytics_service.get_speed_over_time(
        device_id, start_time, end_time, interval_minutes
    )
    
    if speed_data is None:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    return speed_data


@router.get("/heatmap", summary="Get location heatmap data")
async def get_heatmap_data(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    resolution: float = Query(0.001, description="Grid resolution in degrees")
):
    """
    Get location frequency data for heatmap visualization.
    
    Returns aggregated location counts on a grid for creating
    heatmap overlays showing frequently visited areas.
    
    Args:
        start_time: Start of time range
        end_time: End of time range
        resolution: Grid cell size in degrees
        
    Returns:
        Heatmap data with location counts
    """
    if not end_time:
        end_time = datetime.utcnow()
    if not start_time:
        start_time = end_time - timedelta(hours=24)
    
    analytics_service = AnalyticsService()
    heatmap_data = await analytics_service.get_heatmap_data(start_time, end_time, resolution)
    return heatmap_data
"""
Geofence Routes
===============
API endpoints for geofence management.

Endpoints:
    GET /geofences - Get all geofences
    POST /geofences - Create a new geofence
    DELETE /geofences/{id} - Delete a geofence
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List

from backend.api.schemas import GeofenceCreate, GeofenceResponse, CoordinatePoint
from backend.services.geofence_service import GeofenceService

router = APIRouter(prefix="/geofences", tags=["Geofences"])


@router.get("", response_model=List[GeofenceResponse], summary="Get all geofences")
async def get_geofences(
    active_only: bool = Query(True, description="Only return active geofences")
):
    """
    Get all geofences.
    
    Args:
        active_only: If True, only return active geofences
        
    Returns:
        List of geofences with their polygon coordinates
    """
    geofence_service = GeofenceService()
    geofences = await geofence_service.get_all_geofences(active_only=active_only)
    return geofences


@router.get("/{geofence_id}", response_model=GeofenceResponse, summary="Get geofence details")
async def get_geofence(geofence_id: str):
    """
    Get details for a specific geofence.
    
    Args:
        geofence_id: ID of the geofence
        
    Returns:
        Geofence details with polygon coordinates
    """
    geofence_service = GeofenceService()
    geofence = await geofence_service.get_geofence(geofence_id)
    
    if not geofence:
        raise HTTPException(status_code=404, detail=f"Geofence {geofence_id} not found")
    
    return geofence


@router.post("", response_model=GeofenceResponse, summary="Create geofence")
async def create_geofence(geofence_data: GeofenceCreate):
    """
    Create a new geofence.
    
    The geofence is defined as a polygon with at least 3 coordinate points.
    The polygon will be automatically closed if the last point doesn't
    match the first point.
    
    Args:
        geofence_data: Geofence details including polygon coordinates
        
    Returns:
        Created geofence
    """
    geofence_service = GeofenceService()
    geofence = await geofence_service.create_geofence(geofence_data)
    return geofence


@router.put("/{geofence_id}/toggle", response_model=GeofenceResponse, summary="Toggle geofence")
async def toggle_geofence(geofence_id: str):
    """
    Toggle geofence active status.
    
    Args:
        geofence_id: ID of the geofence to toggle
        
    Returns:
        Updated geofence
    """
    geofence_service = GeofenceService()
    geofence = await geofence_service.toggle_geofence(geofence_id)
    
    if not geofence:
        raise HTTPException(status_code=404, detail=f"Geofence {geofence_id} not found")
    
    return geofence


@router.delete("/{geofence_id}", summary="Delete geofence")
async def delete_geofence(geofence_id: str):
    """
    Delete a geofence.
    
    Args:
        geofence_id: ID of the geofence to delete
        
    Returns:
        Success message
    """
    geofence_service = GeofenceService()
    success = await geofence_service.delete_geofence(geofence_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Geofence {geofence_id} not found")
    
    return {"message": f"Geofence {geofence_id} deleted successfully"}

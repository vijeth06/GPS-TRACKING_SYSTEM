/**
 * MapView Component
 * 
 * Interactive map showing:
 * - Device markers with status colors
 * - Device trails (polylines)
 * - Geofence boundaries
 * 
 * Uses Leaflet.js with OpenStreetMap tiles.
 */

import React, { useEffect, useState, useCallback } from 'react'
import { MapContainer, TileLayer, useMap, CircleMarker, Tooltip } from 'react-leaflet'
import DeviceMarker from './DeviceMarker'
import TrailLayer from './TrailLayer'
import GeofenceLayer from './GeofenceLayer'
import { getDeviceTrail } from '../services/api'

// Default map center (Coimbatore, India)
const DEFAULT_CENTER = [11.0168, 76.9558]
const DEFAULT_ZOOM = 12

/**
 * Component to handle map centering on selected device
 */
function MapController({ selectedDevice, devices }) {
  const map = useMap()

  useEffect(() => {
    if (selectedDevice && selectedDevice.latest_location) {
      const { latitude, longitude } = selectedDevice.latest_location
      map.setView([latitude, longitude], 14, { animate: true })
    } else if (devices.length > 0) {
      // Fit bounds to show all devices
      const validDevices = devices.filter(
        (d) => d.latest_location?.latitude && d.latest_location?.longitude
      )
      if (validDevices.length > 0) {
        const bounds = validDevices.map((d) => [
          d.latest_location.latitude,
          d.latest_location.longitude,
        ])
        map.fitBounds(bounds, { padding: [50, 50] })
      }
    }
  }, [selectedDevice, devices, map])

  return null
}

function MapView({ devices, selectedDevice, geofences, onDeviceSelect, replayPoint = null }) {
  const [trail, setTrail] = useState(null)
  const [loadingTrail, setLoadingTrail] = useState(false)

  // Load trail when device is selected
  useEffect(() => {
    const loadTrail = async () => {
      if (!selectedDevice) {
        setTrail(null)
        return
      }

      setLoadingTrail(true)
      try {
        const now = new Date()
        const startTime = new Date(now.getTime() - 4 * 60 * 60 * 1000) // Last 4 hours
        const trailData = await getDeviceTrail(
          selectedDevice.device_id,
          startTime,
          now
        )
        setTrail(trailData)
      } catch (error) {
        console.error('Error loading trail:', error)
        setTrail(null)
      } finally {
        setLoadingTrail(false)
      }
    }

    loadTrail()
  }, [selectedDevice])

  // Calculate initial center
  const getInitialCenter = useCallback(() => {
    const validDevices = devices.filter(
      (d) => d.latest_location?.latitude && d.latest_location?.longitude
    )
    if (validDevices.length > 0) {
      const avgLat =
        validDevices.reduce((sum, d) => sum + d.latest_location.latitude, 0) /
        validDevices.length
      const avgLng =
        validDevices.reduce((sum, d) => sum + d.latest_location.longitude, 0) /
        validDevices.length
      return [avgLat, avgLng]
    }
    return DEFAULT_CENTER
  }, [devices])

  return (
    <div className="h-full w-full relative">
      <MapContainer
        center={getInitialCenter()}
        zoom={DEFAULT_ZOOM}
        className="h-full w-full"
        zoomControl={true}
      >
        {/* OpenStreetMap Tiles */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Map Controller for centering */}
        <MapController selectedDevice={selectedDevice} devices={devices} />

        {/* Geofence boundaries */}
        {geofences.map((geofence) => (
          <GeofenceLayer key={geofence.id} geofence={geofence} />
        ))}

        {/* Device trail for selected device */}
        {trail && trail.points && trail.points.length > 0 && (
          <TrailLayer trail={trail} />
        )}

        {/* Device markers */}
        {devices.map((device) => (
          <DeviceMarker
            key={device.device_id}
            device={device}
            isSelected={selectedDevice?.device_id === device.device_id}
            onClick={() => onDeviceSelect(device)}
          />
        ))}

        {replayPoint && (
          <CircleMarker
            center={[replayPoint.lat, replayPoint.lng]}
            radius={9}
            pathOptions={{
              color: '#1d4ed8',
              fillColor: '#60a5fa',
              fillOpacity: 0.85,
              weight: 2,
            }}
          >
            <Tooltip direction="top" offset={[0, -10]}>
              Replay Point
            </Tooltip>
          </CircleMarker>
        )}
      </MapContainer>

      {/* Loading overlay */}
      {loadingTrail && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-white px-4 py-2 rounded-lg shadow-lg z-[1000]">
          <span className="text-sm text-gray-600">Loading trail...</span>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-white p-3 rounded-lg shadow-lg z-[1000]">
        <h4 className="text-xs font-semibold text-gray-700 mb-2">Status Legend</h4>
        <div className="space-y-1">
          <LegendItem color="bg-green-500" label="Connectivity: Online" />
          <LegendItem color="bg-yellow-500" label="Connectivity: Delayed" />
          <LegendItem color="bg-gray-300" label="Connectivity: Offline" />
          <LegendItem color="bg-gray-500" label="Movement: Stationary" />
          <LegendItem color="bg-yellow-500" label="Movement: Slow (5-20 km/h)" />
          <LegendItem color="bg-green-500" label="Movement: Normal (20-60 km/h)" />
          <LegendItem color="bg-red-500" label="Movement: Fast (>60 km/h)" />
        </div>
      </div>
    </div>
  )
}

function LegendItem({ color, label }) {
  return (
    <div className="flex items-center space-x-2">
      <div className={`w-3 h-3 rounded-full ${color}`} />
      <span className="text-xs text-gray-600">{label}</span>
    </div>
  )
}

export default MapView

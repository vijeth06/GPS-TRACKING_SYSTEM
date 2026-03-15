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

import React, { useEffect, useState, useCallback, useRef } from 'react'
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
  const hasInitialFit = useRef(false)

  useEffect(() => {
    let cancelled = false

    const frame = window.requestAnimationFrame(() => {
      if (cancelled || !map || !map._loaded) {
        return
      }

      try {
        map.stop()

        if (selectedDevice?.latest_location) {
          const { latitude, longitude } = selectedDevice.latest_location
          if (Number.isFinite(latitude) && Number.isFinite(longitude)) {
            map.setView([latitude, longitude], Math.max(map.getZoom(), 14), { animate: false })
          }
          return
        }

        if (!hasInitialFit.current && devices.length > 0) {
          // Fit bounds only once on initial load to show all devices
          const validDevices = devices.filter(
            (d) => Number.isFinite(d.latest_location?.latitude) && Number.isFinite(d.latest_location?.longitude)
          )
          if (validDevices.length > 0) {
            const bounds = validDevices.map((d) => [
              d.latest_location.latitude,
              d.latest_location.longitude,
            ])
            map.fitBounds(bounds, { padding: [50, 50], animate: false })
            hasInitialFit.current = true
          }
        }
      } catch (error) {
        console.error('Map recenter failed:', error)
      }
    })

    return () => {
      cancelled = true
      window.cancelAnimationFrame(frame)
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
        scrollWheelZoom={false}
        zoomAnimation={false}
        markerZoomAnimation={false}
        fadeAnimation={false}
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
      <div className="absolute bottom-4 left-4 right-4 md:right-auto md:w-[370px] bg-white/95 backdrop-blur p-3 rounded-xl shadow-lg border border-slate-200 z-[1000]">
        <h4 className="text-xs font-semibold text-slate-800 mb-2 uppercase tracking-wide">Map Legend</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <p className="text-[11px] font-semibold text-slate-600 mb-1 uppercase tracking-wide">
              Connectivity <span className="normal-case font-normal text-slate-400">(ring + glow)</span>
            </p>
            <div className="space-y-1">
              <LegendItem ring borderColor="border-green-500"  glowColor="shadow-[0_0_0_2px_#22c55e]" label="Online" pulse />
              <LegendItem ring borderColor="border-amber-500"  glowColor="shadow-[0_0_0_2px_#f59e0b]" label="Delayed" />
              <LegendItem ring borderColor="border-gray-400"   glowColor="shadow-[0_0_0_2px_#9ca3af]" label="Offline" />
            </div>
          </div>
          <div>
            <p className="text-[11px] font-semibold text-slate-600 mb-1 uppercase tracking-wide">
              Movement <span className="normal-case font-normal text-slate-400">(marker fill)</span>
            </p>
            <div className="space-y-1">
              <LegendItem color="bg-slate-500"  label="Stationary" />
              <LegendItem color="bg-amber-500"  label="Slow (5–20 km/h)" />
              <LegendItem color="bg-green-500"  label="Normal (20–60 km/h)" />
              <LegendItem color="bg-red-500"    label="Fast (>60 km/h)" />
            </div>
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-slate-200">
          <p className="text-[11px] font-semibold text-slate-600 mb-2 uppercase tracking-wide">
            Trail Route <span className="normal-case font-normal text-slate-400">(selected device path)</span>
          </p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            <TrailLegendLine color="bg-slate-500" label="Stationary" />
            <TrailLegendLine color="bg-amber-500" label="Slow" />
            <TrailLegendLine color="bg-green-500" label="Normal" />
            <TrailLegendLine color="bg-red-500" label="Fast" />
          </div>
        </div>
      </div>
    </div>
  )
}

function LegendItem({ color, label, ring = false, borderColor = '', glowColor = '', pulse = false }) {
  return (
    <div className="flex items-center space-x-2">
      {ring ? (
        <div className="relative flex items-center justify-center w-4 h-4">
          {pulse && (
            <div className={`absolute inset-0 rounded-full border-2 border-green-500 opacity-60 animate-ping`} />
          )}
          <div className={`w-3 h-3 rounded-full border-2 bg-white ${borderColor} ${glowColor}`} />
        </div>
      ) : (
        <div className={`w-3 h-3 rounded-full ${color}`} />
      )}
      <span className="text-xs text-slate-600">{label}</span>
    </div>
  )
}

function TrailLegendLine({ color, label }) {
  return (
    <div className="flex items-center gap-2">
      <div className="relative w-8 h-2">
        <div className="absolute inset-0 rounded-full bg-white border border-slate-300" />
        <div className={`absolute left-0 right-0 top-[2px] h-1 rounded-full ${color}`} />
      </div>
      <span className="text-xs text-slate-600">{label}</span>
    </div>
  )
}

export default MapView

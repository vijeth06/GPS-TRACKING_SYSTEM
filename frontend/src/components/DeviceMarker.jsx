/**
 * DeviceMarker Component
 * 
 * Displays a device marker on the map with:
 * - Color based on movement status
 * - Popup with device details
 * - Click handling for selection
 */

import React, { useMemo } from 'react'
import { Marker, Popup, CircleMarker } from 'react-leaflet'
import L from 'leaflet'

// Connectivity colors
const CONNECTIVITY_COLORS = {
  online: '#22c55e', // green
  delayed: '#f59e0b', // amber
  offline: '#9ca3af', // gray
}

/**
 * Create custom icon for device marker
 */
function createDeviceIcon(connectivityStatus, isSelected) {
  const color = CONNECTIVITY_COLORS[connectivityStatus] || CONNECTIVITY_COLORS.offline
  const size = isSelected ? 40 : 32
  const borderWidth = isSelected ? 4 : 2
  
  return L.divIcon({
    className: 'device-marker',
    html: `
      <div style="
        width: ${size}px;
        height: ${size}px;
        background-color: ${color};
        border: ${borderWidth}px solid white;
        border-radius: 50%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          viewBox="0 0 24 24" 
          fill="white" 
          width="${size * 0.5}px" 
          height="${size * 0.5}px"
        >
          <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
        </svg>
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

/**
 * Format speed for display
 */
function formatSpeed(speed) {
  if (speed === null || speed === undefined) return 'N/A'
  return `${speed.toFixed(1)} km/h`
}

/**
 * Format timestamp for display
 */
function formatTime(timestamp) {
  if (!timestamp) return 'N/A'
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

/**
 * Get status display text
 */
function getConnectivityText(status) {
  const statusMap = {
    online: 'Online',
    delayed: 'Delayed',
    offline: 'Offline',
  }
  return statusMap[status] || 'Unknown'
}

function getMovementText(status) {
  const statusMap = {
    stationary: 'Stationary',
    slow: 'Slow Moving',
    normal: 'Normal Speed',
    fast: 'High Speed',
  }
  return statusMap[status] || 'Unknown'
}

function DeviceMarker({ device, isSelected, onClick }) {
  const { latest_location } = device
  
  // Skip if no location
  if (!latest_location?.latitude || !latest_location?.longitude) {
    return null
  }

  const position = [latest_location.latitude, latest_location.longitude]
  const connectivityStatus = device.connection_status || 'offline'
  const movementStatus = device.movement_status || 'unknown'

  const icon = useMemo(
    () => createDeviceIcon(connectivityStatus, isSelected),
    [connectivityStatus, isSelected]
  )

  return (
    <Marker
      position={position}
      icon={icon}
      eventHandlers={{
        click: onClick,
      }}
    >
      <Popup>
        <div className="p-2 min-w-[200px]">
          <h3 className="font-bold text-lg text-gray-900">
            {device.device_name || device.device_id}
          </h3>
          <p className="text-sm text-gray-500 mb-2">{device.device_id}</p>
          
          <div className="space-y-2">
            {/* Status */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Connectivity:</span>
              <span 
                className="px-2 py-1 rounded-full text-xs font-medium"
                style={{ 
                  backgroundColor: `${CONNECTIVITY_COLORS[connectivityStatus]}20`,
                  color: CONNECTIVITY_COLORS[connectivityStatus]
                }}
              >
                {getConnectivityText(connectivityStatus)}
              </span>
            </div>

            {/* Movement */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Movement:</span>
              <span className="text-sm font-medium">{getMovementText(movementStatus)}</span>
            </div>
            
            {/* Speed */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Speed:</span>
              <span className="text-sm font-medium">
                {formatSpeed(latest_location.speed)}
              </span>
            </div>
            
            {/* Position */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Position:</span>
              <span className="text-sm font-mono">
                {latest_location.latitude.toFixed(4)}, {latest_location.longitude.toFixed(4)}
              </span>
            </div>
            
            {/* Last Update */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Last Update:</span>
              <span className="text-sm">
                {formatTime(latest_location.timestamp)}
              </span>
            </div>
          </div>
        </div>
      </Popup>
    </Marker>
  )
}

export default DeviceMarker

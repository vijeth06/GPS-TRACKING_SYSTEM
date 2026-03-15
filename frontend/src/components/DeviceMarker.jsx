
import React, { useMemo } from 'react'
import { Marker, Popup, CircleMarker } from 'react-leaflet'
import L from 'leaflet'

const CONNECTIVITY_BORDER_COLORS = {
  online: '#22c55e',   // green-500
  delayed: '#f59e0b',  // amber-500
  offline: '#9ca3af',  // gray-400
}

const MOVEMENT_FILL_COLORS = {
  stationary: '#64748b', // slate-500
  slow: '#f59e0b',       // amber-500
  normal: '#22c55e',     // green-500
  fast: '#ef4444',       // red-500
  unknown: '#94a3b8',    // slate-400
}

const CONNECTIVITY_GLOW = {
  online:  '0 0 0 3px #22c55e, 0 0 12px 4px rgba(34,197,94,0.55)',
  delayed: '0 0 0 3px #f59e0b, 0 0 12px 4px rgba(245,158,11,0.50)',
  offline: '0 0 0 3px #9ca3af, 0 0  6px 2px rgba(156,163,175,0.35)',
}

const CONNECTIVITY_RING_CLASS = {
  online:  'marker-ring-pulse',
  delayed: 'marker-ring-throb',
  offline: '',
}

const CONNECTIVITY_DOT_COLOR = {
  online:  '#16a34a',
  delayed: '#d97706',
  offline: '#6b7280',
}

function createDeviceIcon(connectivityStatus, movementStatus, isSelected) {
  const borderColor = CONNECTIVITY_BORDER_COLORS[connectivityStatus] || CONNECTIVITY_BORDER_COLORS.offline
  const fillColor   = MOVEMENT_FILL_COLORS[movementStatus]           || MOVEMENT_FILL_COLORS.unknown
  const glow        = CONNECTIVITY_GLOW[connectivityStatus]          || CONNECTIVITY_GLOW.offline
  const ringClass   = CONNECTIVITY_RING_CLASS[connectivityStatus]    || ''
  const dotColor    = CONNECTIVITY_DOT_COLOR[connectivityStatus]     || CONNECTIVITY_DOT_COLOR.offline

  const size        = isSelected ? 42 : 34
  const dotSize     = isSelected ? 11 : 9
  const iconSvg     = size * 0.48
  const wrapSize    = size + 14

  return L.divIcon({
    className: 'device-marker',
    html: `
      <div style="
        position: relative;
        width: ${wrapSize}px;
        height: ${wrapSize}px;
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        ${ringClass ? `<div class="${ringClass}"></div>` : ''}
        <div style="
          position: relative;
          width: ${size}px;
          height: ${size}px;
          background-color: ${fillColor};
          border: 3px solid ${borderColor};
          border-radius: 50%;
          box-shadow: ${glow}, 0 3px 8px rgba(0,0,0,0.30);
          display: flex;
          align-items: center;
          justify-content: center;
          transition: transform 0.15s;
        ">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="rgba(255,255,255,0.92)"
            width="${iconSvg}px"
            height="${iconSvg}px"
          >
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
          </svg>
          <div style="
            position: absolute;
            bottom: -2px;
            right: -2px;
            width: ${dotSize}px;
            height: ${dotSize}px;
            background-color: ${dotColor};
            border: 2px solid white;
            border-radius: 50%;
            box-shadow: 0 1px 4px rgba(0,0,0,0.4);
          "></div>
        </div>
      </div>
    `,
    iconSize: [wrapSize, wrapSize],
    iconAnchor: [wrapSize / 2, wrapSize / 2],
  })
}

function formatSpeed(speed) {
  if (speed === null || speed === undefined) return 'N/A'
  return `${speed.toFixed(1)} km/h`
}

function formatTime(timestamp) {
  if (!timestamp) return 'N/A'
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

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
  
  if (!latest_location?.latitude || !latest_location?.longitude) {
    return null
  }

  const position = [latest_location.latitude, latest_location.longitude]
  const connectivityStatus = device.connection_status || 'offline'
  const movementStatus = device.movement_status || 'unknown'

  const icon = useMemo(
    () => createDeviceIcon(connectivityStatus, movementStatus, isSelected),
    [connectivityStatus, movementStatus, isSelected]
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
                  backgroundColor: `${CONNECTIVITY_BORDER_COLORS[connectivityStatus]}20`,
                  color: CONNECTIVITY_BORDER_COLORS[connectivityStatus]
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
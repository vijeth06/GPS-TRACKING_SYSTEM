/**
 * GeofenceLayer Component
 * 
 * Displays geofence polygon boundaries on the map.
 * Color indicates fence type (restricted, allowed, warning).
 */

import React from 'react'
import { Polygon, Tooltip } from 'react-leaflet'

// Geofence colors by type
const FENCE_COLORS = {
  restricted: {
    color: '#ef4444', // Red
    fillColor: '#ef4444',
  },
  allowed: {
    color: '#22c55e', // Green
    fillColor: '#22c55e',
  },
  warning: {
    color: '#f59e0b', // Yellow
    fillColor: '#f59e0b',
  },
}

function GeofenceLayer({ geofence }) {
  if (!geofence || !geofence.coordinates || geofence.coordinates.length < 3) {
    return null
  }

  // Convert coordinates to Leaflet format
  const positions = geofence.coordinates.map((coord) => [coord.lat, coord.lng])

  // Get colors based on fence type
  const colors = FENCE_COLORS[geofence.fence_type] || FENCE_COLORS.warning

  return (
    <Polygon
      positions={positions}
      pathOptions={{
        color: colors.color,
        fillColor: colors.fillColor,
        fillOpacity: 0.2,
        weight: 2,
        dashArray: geofence.fence_type === 'warning' ? '5, 5' : null,
      }}
    >
      <Tooltip direction="center" permanent={false}>
        <div className="p-1">
          <p className="font-semibold text-sm">{geofence.name}</p>
          <p className="text-xs text-gray-600 capitalize">{geofence.fence_type} Zone</p>
          {geofence.description && (
            <p className="text-xs text-gray-500 mt-1">{geofence.description}</p>
          )}
        </div>
      </Tooltip>
    </Polygon>
  )
}

export default GeofenceLayer

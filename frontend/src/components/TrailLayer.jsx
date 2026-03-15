/**
 * TrailLayer Component
 * 
 * Displays the movement trail for a device as a polyline.
 * Color gradient indicates speed at each point.
 */

import React from 'react'
import { Polyline, CircleMarker, Tooltip } from 'react-leaflet'

// Trail colors
const TRAIL_COLOR = '#2563eb' // Blue
const TRAIL_START_COLOR = '#22c55e' // Green
const TRAIL_END_COLOR = '#ef4444' // Red

function TrailLayer({ trail }) {
  if (!trail || !trail.points || trail.points.length < 2) {
    return null
  }

  // Convert points to position array
  const positions = trail.points.map((point) => [point.lat, point.lng])

  // Calculate trail segments with speed-based coloring
  const segments = []
  for (let i = 1; i < trail.points.length; i++) {
    const startPoint = trail.points[i - 1]
    const endPoint = trail.points[i]
    const speed = endPoint.speed || 0
    
    // Color based on speed
    let color
    if (speed < 5) {
      color = '#6b7280' // Gray - stationary
    } else if (speed < 20) {
      color = '#f59e0b' // Yellow - slow
    } else if (speed < 60) {
      color = '#22c55e' // Green - normal
    } else {
      color = '#ef4444' // Red - fast
    }

    segments.push({
      positions: [
        [startPoint.lat, startPoint.lng],
        [endPoint.lat, endPoint.lng],
      ],
      color,
      speed,
    })
  }

  // Start and end points
  const startPoint = trail.points[0]
  const endPoint = trail.points[trail.points.length - 1]

  return (
    <>
      {/* High-contrast casing for readability on mixed map backgrounds */}
      <Polyline
        positions={positions}
        pathOptions={{
          color: '#ffffff',
          weight: 9,
          opacity: 0.92,
          lineCap: 'round',
          lineJoin: 'round',
        }}
      />

      {/* Main route backbone */}
      <Polyline
        positions={positions}
        pathOptions={{
          color: TRAIL_COLOR,
          weight: 5,
          opacity: 0.85,
          lineCap: 'round',
          lineJoin: 'round',
        }}
      />

      {/* Speed-colored segments overlay */}
      {segments.map((segment, index) => (
        <Polyline
          key={index}
          positions={segment.positions}
          pathOptions={{
            color: segment.color,
            weight: 6,
            opacity: 0.96,
            lineCap: 'round',
            lineJoin: 'round',
          }}
        />
      ))}

      {/* Start point marker */}
      <CircleMarker
        center={[startPoint.lat, startPoint.lng]}
        radius={9}
        pathOptions={{
          color: '#fff',
          fillColor: TRAIL_START_COLOR,
          fillOpacity: 1,
          weight: 3,
        }}
      >
        <Tooltip permanent direction="top" offset={[0, -10]}>
          <span className="text-xs font-medium">Start</span>
        </Tooltip>
      </CircleMarker>

      {/* End point marker */}
      <CircleMarker
        center={[endPoint.lat, endPoint.lng]}
        radius={9}
        pathOptions={{
          color: '#fff',
          fillColor: TRAIL_END_COLOR,
          fillOpacity: 1,
          weight: 3,
        }}
      >
        <Tooltip permanent direction="top" offset={[0, -10]}>
          <span className="text-xs font-medium">Current</span>
        </Tooltip>
      </CircleMarker>

      {/* Trail info overlay */}
      {trail.total_distance !== undefined && (
        <div className="absolute top-4 right-4 bg-white px-4 py-2 rounded-lg shadow-lg z-[1000]">
          <div className="text-sm">
            <span className="text-gray-600">Total Distance:</span>
            <span className="ml-2 font-semibold">{trail.total_distance.toFixed(2)} km</span>
          </div>
          <div className="text-sm">
            <span className="text-gray-600">Points:</span>
            <span className="ml-2 font-semibold">{trail.points.length}</span>
          </div>
        </div>
      )}
    </>
  )
}

export default TrailLayer

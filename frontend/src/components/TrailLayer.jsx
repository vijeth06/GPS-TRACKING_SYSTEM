
import React from 'react'
import { Polyline, CircleMarker, Tooltip } from 'react-leaflet'

const TRAIL_COLOR = '#2563eb' // Blue
const TRAIL_START_COLOR = '#22c55e' // Green
const TRAIL_END_COLOR = '#ef4444' // Red
const MAX_RENDER_POINTS = 180
const MAX_SEGMENT_JUMP_KM = 0.8

function haversineKm(aLat, aLng, bLat, bLng) {
  const toRad = (deg) => (deg * Math.PI) / 180
  const R = 6371
  const dLat = toRad(bLat - aLat)
  const dLng = toRad(bLng - aLng)
  const aa =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(aLat)) * Math.cos(toRad(bLat)) *
    Math.sin(dLng / 2) * Math.sin(dLng / 2)
  const c = 2 * Math.atan2(Math.sqrt(aa), Math.sqrt(1 - aa))
  return R * c
}

function TrailLayer({ trail }) {
  if (!trail || !trail.points || trail.points.length < 2) {
    return null
  }

  const stride = Math.max(1, Math.ceil(trail.points.length / MAX_RENDER_POINTS))
  const sampledPoints = trail.points.filter(
    (point, index) => index % stride === 0 || index === trail.points.length - 1
  )

  const cleanPoints = []
  for (const point of sampledPoints) {
    if (!Number.isFinite(point.lat) || !Number.isFinite(point.lng)) {
      continue
    }
    if (cleanPoints.length === 0) {
      cleanPoints.push(point)
      continue
    }
    const prev = cleanPoints[cleanPoints.length - 1]
    const jumpKm = haversineKm(prev.lat, prev.lng, point.lat, point.lng)
    if (jumpKm <= MAX_SEGMENT_JUMP_KM) {
      cleanPoints.push(point)
    }
  }

  if (cleanPoints.length < 2) {
    return null
  }

  const positions = cleanPoints.map((point) => [point.lat, point.lng])

  const segments = []
  for (let i = 1; i < cleanPoints.length; i++) {
    const startPoint = cleanPoints[i - 1]
    const endPoint = cleanPoints[i]
    const speed = endPoint.speed || 0
    
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

  const startPoint = cleanPoints[0]
  const endPoint = cleanPoints[cleanPoints.length - 1]

  return (
    <>
      {/* High-contrast casing for readability on mixed map backgrounds */}
      <Polyline
        positions={positions}
        pathOptions={{
          color: '#ffffff',
          weight: 6,
          opacity: 0.9,
          lineCap: 'round',
          lineJoin: 'round',
        }}
      />

      {/* Main route backbone */}
      <Polyline
        positions={positions}
        pathOptions={{
          color: TRAIL_COLOR,
          weight: 3,
          opacity: 0.7,
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
            weight: 3.5,
            opacity: 0.9,
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
            <span className="ml-2 font-semibold">{cleanPoints.length} / {trail.points.length}</span>
          </div>
        </div>
      )}
    </>
  )
}

export default TrailLayer
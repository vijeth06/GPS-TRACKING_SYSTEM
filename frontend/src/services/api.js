/**
 * API Service
 * 
 * Handles HTTP requests to the backend API.
 */

import axios from 'axios'

const API_BASE_URL = '/api'
const INGEST_TOKEN = import.meta.env.VITE_INGEST_TOKEN || ''

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// =============================================================================
// DEVICE ENDPOINTS
// =============================================================================

/**
 * Get all devices with their latest locations
 */
export const getDevices = async () => {
  const response = await api.get('/devices')
  return response.data
}

/**
 * Get a specific device with location
 */
export const getDevice = async (deviceId) => {
  const response = await api.get(`/device/${deviceId}`)
  return response.data
}

/**
 * Get device trail/movement history
 */
export const getDeviceTrail = async (deviceId, startTime, endTime) => {
  const params = {}
  if (startTime) params.start_time = startTime.toISOString()
  if (endTime) params.end_time = endTime.toISOString()
  
  const response = await api.get(`/device/${deviceId}/trail`, { params })
  return response.data
}

// =============================================================================
// ALERT ENDPOINTS
// =============================================================================

/**
 * Get alerts with optional filters
 */
export const getAlerts = async (filters = {}) => {
  const params = {}
  if (filters.deviceId) params.device_id = filters.deviceId
  if (filters.alertType) params.alert_type = filters.alertType
  if (filters.limit) params.limit = filters.limit
  
  const response = await api.get('/alerts', { params })
  return response.data
}

/**
 * Get unacknowledged alerts
 */
export const getUnacknowledgedAlerts = async (limit = 50) => {
  const response = await api.get('/alerts/unacknowledged', { params: { limit } })
  return response.data
}

/**
 * Acknowledge an alert
 */
export const acknowledgeAlert = async (alertId) => {
  const response = await api.post(`/alerts/${alertId}/acknowledge`)
  return response.data
}

/**
 * Resolve an alert
 */
export const resolveAlert = async (alertId, resolutionNote = '') => {
  const response = await api.post(`/alerts/${alertId}/resolve`, {
    resolution_note: resolutionNote,
  })
  return response.data
}

// =============================================================================
// GEOFENCE ENDPOINTS
// =============================================================================

/**
 * Get all geofences
 */
export const getGeofences = async (activeOnly = true) => {
  const response = await api.get('/geofences', { params: { active_only: activeOnly } })
  return response.data
}

/**
 * Create a new geofence
 */
export const createGeofence = async (geofenceData) => {
  const response = await api.post('/geofences', geofenceData)
  return response.data
}

/**
 * Delete a geofence
 */
export const deleteGeofence = async (geofenceId) => {
  const response = await api.delete(`/geofences/${geofenceId}`)
  return response.data
}

// =============================================================================
// ANALYTICS ENDPOINTS
// =============================================================================

/**
 * Get device analytics
 */
export const getDeviceAnalytics = async (deviceId, startTime, endTime) => {
  const params = {}
  if (startTime) params.start_time = startTime.toISOString()
  if (endTime) params.end_time = endTime.toISOString()
  
  const response = await api.get(`/analytics/device/${deviceId}`, { params })
  return response.data
}

/**
 * Get system-wide analytics
 */
export const getSystemAnalytics = async () => {
  const response = await api.get('/analytics/system')
  return response.data
}

/**
 * Get speed over time data for charts
 */
export const getSpeedOverTime = async (deviceId, startTime, endTime, interval = 5) => {
  const params = { interval_minutes: interval }
  if (startTime) params.start_time = startTime.toISOString()
  if (endTime) params.end_time = endTime.toISOString()
  
  const response = await api.get(`/analytics/speed/${deviceId}`, { params })
  return response.data
}

/**
 * Get heatmap data
 */
export const getHeatmapData = async (startTime, endTime) => {
  const params = {}
  if (startTime) params.start_time = startTime.toISOString()
  if (endTime) params.end_time = endTime.toISOString()
  
  const response = await api.get('/analytics/heatmap', { params })
  return response.data
}

// =============================================================================
// WORKFLOW / OPS ENDPOINTS
// =============================================================================

/**
 * Get operational snapshot metrics
 */
export const getOpsSnapshot = async () => {
  const response = await api.get('/ops/snapshot')
  return response.data
}

/**
 * Get ingestion worker status
 */
export const getIngestionStatus = async () => {
  const response = await api.get('/ingest/status')
  return response.data
}

/**
 * Submit a raw GPS packet to ingestion endpoint
 */
export const ingestRawPacket = async (packet, token = '') => {
  const headers = {}
  const effectiveToken = token || INGEST_TOKEN
  if (effectiveToken) {
    headers['X-Ingest-Token'] = effectiveToken
  }

  const response = await api.post('/ingest/raw', packet, {
    headers,
  })
  return response.data
}

/**
 * List GeoServer layers configured in backend
 */
export const getGeoserverLayers = async () => {
  const response = await api.get('/geoserver/layers')
  return response.data
}

/**
 * Trigger GeoServer WFS sync to geofences
 */
export const syncGeoserverLayers = async () => {
  const response = await api.post('/geoserver/sync')
  return response.data
}

/**
 * Trigger demo geofence violation setup
 */
export const triggerDemoGeofence = async () => {
  const response = await api.post('/demo/geofence-violation')
  return response.data
}

/**
 * Trigger demo stationary behavior setup
 */
export const triggerDemoStationary = async (deviceId = 'TRK101') => {
  const response = await api.post('/demo/stationary', null, {
    params: { device_id: deviceId },
  })
  return response.data
}

export default api

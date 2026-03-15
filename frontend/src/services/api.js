
import axios from 'axios'

const API_BASE_URL = '/api'
const INGEST_TOKEN = import.meta.env.VITE_INGEST_TOKEN || ''
const AUTH_TOKEN_KEY = 'gps_auth_token'

export const getAuthToken = () => localStorage.getItem(AUTH_TOKEN_KEY) || ''
export const setAuthToken = (token) => {
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token)
  } else {
    localStorage.removeItem(AUTH_TOKEN_KEY)
  }
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})


export const login = async (username, password) => {
  const response = await api.post('/auth/login', { username, password })
  if (response.data?.access_token) {
    setAuthToken(response.data.access_token)
  }
  return response.data
}

export const getCurrentUser = async () => {
  const response = await api.get('/auth/me')
  return response.data
}

export const logout = () => {
  setAuthToken('')
}


export const getDevices = async () => {
  const response = await api.get('/devices')
  return response.data
}

export const getDevice = async (deviceId) => {
  const response = await api.get(`/device/${deviceId}`)
  return response.data
}

export const onboardDevice = async (payload) => {
  const response = await api.post('/devices/onboard', payload)
  return response.data
}

export const updateDevice = async (deviceId, payload) => {
  const response = await api.put(`/devices/${deviceId}`, payload)
  return response.data
}

export const deleteDevice = async (deviceId) => {
  const response = await api.delete(`/devices/${deviceId}`)
  return response.data
}

export const rotateDeviceCredential = async (deviceId) => {
  const response = await api.post(`/devices/${deviceId}/credentials/rotate`)
  return response.data
}

export const getDeviceCredentialStatus = async (deviceId) => {
  const response = await api.get(`/devices/${deviceId}/credentials/status`)
  return response.data
}

export const getDeviceTrail = async (deviceId, startTime, endTime) => {
  const params = {}
  if (startTime) params.start_time = startTime.toISOString()
  if (endTime) params.end_time = endTime.toISOString()
  
  const response = await api.get(`/device/${deviceId}/trail`, { params })
  return response.data
}


export const getAlerts = async (filters = {}) => {
  const params = {}
  if (filters.deviceId) params.device_id = filters.deviceId
  if (filters.alertType) params.alert_type = filters.alertType
  if (filters.limit) params.limit = filters.limit
  
  const response = await api.get('/alerts', { params })
  return response.data
}

export const getUnacknowledgedAlerts = async (limit = 50) => {
  const response = await api.get('/alerts/unacknowledged', { params: { limit } })
  return response.data
}

export const acknowledgeAlert = async (alertId) => {
  const response = await api.post(`/alerts/${alertId}/acknowledge`)
  return response.data
}

export const resolveAlert = async (alertId, resolutionNote = '') => {
  const response = await api.post(`/alerts/${alertId}/resolve`, {
    resolution_note: resolutionNote,
  })
  return response.data
}

export const assignAlert = async (alertId, assignedTo, assignmentNote = '') => {
  const response = await api.post(`/alerts/${alertId}/assign`, {
    assigned_to: assignedTo,
    assignment_note: assignmentNote,
  })
  return response.data
}

export const escalateAlert = async (alertId, escalationNote = '') => {
  const response = await api.post(`/alerts/${alertId}/escalate`, {
    escalation_note: escalationNote,
  })
  return response.data
}


export const getGeofences = async (activeOnly = true) => {
  const response = await api.get('/geofences', { params: { active_only: activeOnly } })
  return response.data
}

export const createGeofence = async (geofenceData) => {
  const response = await api.post('/geofences', geofenceData)
  return response.data
}

export const deleteGeofence = async (geofenceId) => {
  const response = await api.delete(`/geofences/${geofenceId}`)
  return response.data
}


export const getDeviceAnalytics = async (deviceId, startTime, endTime) => {
  const params = {}
  if (startTime) params.start_time = startTime.toISOString()
  if (endTime) params.end_time = endTime.toISOString()
  
  const response = await api.get(`/analytics/device/${deviceId}`, { params })
  return response.data
}

export const getSystemAnalytics = async () => {
  const response = await api.get('/analytics/system')
  return response.data
}

export const getSpeedOverTime = async (deviceId, startTime, endTime, interval = 5) => {
  const params = { interval_minutes: interval }
  if (startTime) params.start_time = startTime.toISOString()
  if (endTime) params.end_time = endTime.toISOString()
  
  const response = await api.get(`/analytics/speed/${deviceId}`, { params })
  return response.data
}

export const getHeatmapData = async (startTime, endTime) => {
  const params = {}
  if (startTime) params.start_time = startTime.toISOString()
  if (endTime) params.end_time = endTime.toISOString()
  
  const response = await api.get('/analytics/heatmap', { params })
  return response.data
}


export const getOpsSnapshot = async () => {
  const response = await api.get('/ops/snapshot')
  return response.data
}

export const getIngestionStatus = async () => {
  const response = await api.get('/ingest/status')
  return response.data
}

export const ingestRawPacket = async (packet, options = {}) => {
  const headers = {}
  const effectiveToken = typeof options === 'string' ? options : options.token || INGEST_TOKEN
  const deviceKey = typeof options === 'string' ? '' : options.deviceKey || ''
  if (effectiveToken) {
    headers['X-Ingest-Token'] = effectiveToken
  }
  if (deviceKey) {
    headers['X-Device-Key'] = deviceKey
  }

  const response = await api.post('/ingest/raw', packet, {
    headers,
  })
  return response.data
}

export const getStreamListenerStatus = async () => {
  try {
    const response = await api.get('/ingest/stream/status')
    return response.data
  } catch (error) {
    if (error?.response?.status === 404) {
      return {
        running: false,
        protocol: 'udp',
        host: '0.0.0.0',
        port: 9100,
        dataset_profile: 'flexible',
        received_count: 0,
        parsed_count: 0,
        rejected_count: 0,
        last_packet_at: null,
        last_error: 'Stream listener endpoint not available on current backend build',
      }
    }
    throw error
  }
}

export const startStreamListener = async (payload = {}) => {
  const response = await api.post('/ingest/stream/start', payload)
  return response.data
}

export const stopStreamListener = async () => {
  const response = await api.post('/ingest/stream/stop')
  return response.data
}

export const getGeoserverLayers = async () => {
  const response = await api.get('/geoserver/layers')
  return response.data
}

export const getGeoserverConfig = async () => {
  const response = await api.get('/geoserver/config')
  return response.data
}

export const updateGeoserverLayers = async (layerNames = []) => {
  const response = await api.put('/geoserver/config/layers', { layer_names: layerNames })
  return response.data
}

export const clearGeoserverCache = async () => {
  const response = await api.delete('/geoserver/cache')
  return response.data
}

export const syncGeoserverLayers = async () => {
  const response = await api.post('/geoserver/sync')
  return response.data
}

export const getOpenIncidents = async (limit = 20) => {
  const response = await api.get('/incidents/open', { params: { limit } })
  return response.data
}

export const getIncidentWorkspace = async (alertId) => {
  const response = await api.get(`/incidents/${alertId}/workspace`)
  return response.data
}

export const getRetentionStatus = async () => {
  const response = await api.get('/retention/status')
  return response.data
}

export const runRetentionNow = async () => {
  const response = await api.post('/retention/run')
  return response.data
}


export const getNotificationChannels = async () => {
  const response = await api.get('/notifications/channels')
  return response.data
}

export const saveNotificationChannel = async (payload) => {
  const response = await api.post('/notifications/channels', payload)
  return response.data
}

export const testNotificationChannel = async (channelId, payload) => {
  const response = await api.post(`/notifications/channels/${channelId}/test`, payload)
  return response.data
}

export const getAutomationRules = async () => {
  const response = await api.get('/rules')
  return response.data
}

export const createAutomationRule = async (payload) => {
  const response = await api.post('/rules', payload)
  return response.data
}

export const getRoutePlans = async (deviceId = '') => {
  const response = await api.get('/routes', {
    params: deviceId ? { device_id: deviceId } : {},
  })
  return response.data
}

export const createRoutePlan = async (payload) => {
  const response = await api.post('/routes', payload)
  return response.data
}

export const getAdminUsers = async () => {
  const response = await api.get('/admin/users')
  return response.data
}

export const createAdminUser = async (payload) => {
  const response = await api.post('/admin/users', payload)
  return response.data
}

export const getTeams = async () => {
  const response = await api.get('/admin/teams')
  return response.data
}

export const createTeam = async (payload) => {
  const response = await api.post('/admin/teams', payload)
  return response.data
}

export const getReportingSummary = async (hours = 24) => {
  const response = await api.get('/reporting/summary', { params: { hours } })
  return response.data
}

export const getGovernanceSettings = async () => {
  const response = await api.get('/governance/settings')
  return response.data
}

export const updateGovernanceSettings = async (payload) => {
  const response = await api.put('/governance/settings', payload)
  return response.data
}

export const getAnomalyInsight = async (deviceId, speed = 0) => {
  const response = await api.get('/intelligence/anomaly', { params: { device_id: deviceId, speed } })
  return response.data
}

export default api
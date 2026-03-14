/**
 * Dashboard Page
 * 
 * Main dashboard showing:
 * - Interactive map with live device positions
 * - Analytics panel
 * - Alerts feed
 * - Device list
 * 
 * Layout:
 * +----------------------------------+
 * |         Header / Stats          |
 * +----------------------------------+
 * |                    |   Analytics |
 * |      Map View      |   Panel     |
 * |                    |   & Alerts  |
 * +----------------------------------+
 */

import React, { useState, useEffect, useCallback } from 'react'
import { 
  MapPin, Activity, AlertTriangle, Truck, 
  Timer, Gauge, Route, Bell 
} from 'lucide-react'
import MapView from '../components/MapView'
import DeviceList from '../components/DeviceList'
import AlertPanel from '../components/AlertPanel'
import AnalyticsDashboard from '../components/AnalyticsDashboard'
import WorkflowPanel from '../components/WorkflowPanel'
import RouteReplayTimeline from '../components/RouteReplayTimeline'
import IncidentWorkspace from '../components/IncidentWorkspace'
import { getDevices, getAlerts, getGeofences, getSystemAnalytics } from '../services/api'
import socketService from '../services/socket'
import { useAuth } from '../context/AuthContext'

function Dashboard() {
  const { user, logout } = useAuth()
  // State
  const [devices, setDevices] = useState([])
  const [selectedDevice, setSelectedDevice] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [geofences, setGeofences] = useState([])
  const [systemStats, setSystemStats] = useState({
    total_devices: 0,
    devices_online: 0,
    total_alerts: 0,
    unacknowledged_alerts: 0,
  })
  const [isConnected, setIsConnected] = useState(false)
  const [loading, setLoading] = useState(true)
  const [replayPoint, setReplayPoint] = useState(null)
  const [selectedAlert, setSelectedAlert] = useState(null)

  // Initial data fetch
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const [devicesData, alertsData, geofencesData, statsData] = await Promise.all([
          getDevices(),
          getAlerts({ limit: 50 }),
          getGeofences(),
          getSystemAnalytics(),
        ])
        
        setDevices(devicesData)
        setAlerts(alertsData)
        setGeofences(geofencesData)
        setSystemStats(statsData)
      } catch (error) {
        console.error('Error fetching data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    // Refresh data periodically
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  // WebSocket connection
  useEffect(() => {
    const connectSocket = async () => {
      try {
        await socketService.connect()
        setIsConnected(true)
      } catch (error) {
        console.error('Socket connection failed:', error)
        setIsConnected(false)
      }
    }

    connectSocket()

    return () => {
      socketService.disconnect()
    }
  }, [])

  // Listen for real-time updates
  useEffect(() => {
    if (!isConnected) return

    // Location updates
    const unsubLocation = socketService.onLocationUpdate((data) => {
      setDevices((prevDevices) => {
        return prevDevices.map((device) => {
          if (device.device_id === data.device_id) {
            const currentLatest = device.latest_location || {}
            return {
              ...device,
              latest_location: {
                ...currentLatest,
                latitude: data.lat,
                longitude: data.lng,
                speed: data.speed,
                timestamp: data.timestamp,
              },
              movement_status: data.status || device.movement_status || 'unknown',
              connection_status: 'online',
              last_seen: data.timestamp,
            }
          }
          return device
        })
      })
    })

    // Alert updates
    const unsubAlert = socketService.onAlertUpdate((data) => {
      setAlerts((prevAlerts) => [data, ...prevAlerts.slice(0, 49)])
      setSystemStats((prev) => ({
        ...prev,
        total_alerts: prev.total_alerts + 1,
        unacknowledged_alerts: prev.unacknowledged_alerts + 1,
      }))
    })

    return () => {
      unsubLocation()
      unsubAlert()
    }
  }, [isConnected])

  // Select device handler
  const handleDeviceSelect = useCallback((device) => {
    setSelectedDevice(device)
  }, [])

  // Acknowledge alert handler
  const handleAlertChanged = useCallback((updatedAlert) => {
    if (!updatedAlert?.id) return

    setAlerts((prevAlerts) =>
      prevAlerts.map((alert) => (alert.id === updatedAlert.id ? { ...alert, ...updatedAlert } : alert))
    )

    if (updatedAlert.is_acknowledged) {
      setSystemStats((prev) => ({
        ...prev,
        unacknowledged_alerts: Math.max(0, prev.unacknowledged_alerts - 1),
      }))
    }
  }, [])

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-full mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-blue-600 p-2 rounded-lg">
                <MapPin className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  GPS Tracking System
                </h1>
                <p className="text-sm text-gray-500">
                  Real-Time Movement Intelligence
                </p>
              </div>
            </div>
            
            {/* Connection Status */}
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm font-medium text-gray-700">{user?.username}</p>
                <p className="text-xs text-gray-500 uppercase tracking-wide">{user?.role}</p>
              </div>
              <div className="flex items-center space-x-2">
                <div
                  className={`w-3 h-3 rounded-full ${
                    isConnected ? 'bg-green-500 pulse-animation' : 'bg-red-500'
                  }`}
                />
                <span className="text-sm text-gray-600">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              <button
                type="button"
                onClick={logout}
                className="text-sm px-3 py-1 rounded bg-gray-100 hover:bg-gray-200"
              >
                Logout
              </button>
            </div>
          </div>

          {/* Stats Bar */}
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              icon={<Truck className="w-5 h-5" />}
              label="Total Devices"
              value={systemStats.total_devices}
              color="blue"
            />
            <StatCard
              icon={<Activity className="w-5 h-5" />}
              label="Online Now"
              value={systemStats.devices_online}
              color="green"
            />
            <StatCard
              icon={<AlertTriangle className="w-5 h-5" />}
              label="Total Alerts"
              value={systemStats.total_alerts}
              color="yellow"
            />
            <StatCard
              icon={<Bell className="w-5 h-5" />}
              label="Unacknowledged"
              value={systemStats.unacknowledged_alerts}
              color="red"
            />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-full mx-auto px-4 py-4">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 h-[calc(100vh-220px)]">
          {/* Map Section - Takes 3/4 on large screens */}
          <div className="lg:col-span-3 bg-white rounded-lg shadow-sm overflow-hidden">
            {loading ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-gray-500">Loading map...</div>
              </div>
            ) : (
              <MapView
                devices={devices}
                selectedDevice={selectedDevice}
                geofences={geofences}
                onDeviceSelect={handleDeviceSelect}
                replayPoint={replayPoint}
              />
            )}
          </div>

          {/* Right Panel - Analytics, Devices, Alerts */}
          <div className="lg:col-span-1 flex flex-col space-y-4 overflow-hidden">
            {/* Device List */}
            <div className="bg-white rounded-lg shadow-sm p-4 max-h-[300px] overflow-auto custom-scrollbar">
              <h2 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
                <Truck className="w-5 h-5 mr-2 text-blue-600" />
                Devices
              </h2>
              <DeviceList
                devices={devices}
                selectedDevice={selectedDevice}
                onDeviceSelect={handleDeviceSelect}
              />
            </div>

            {/* Analytics */}
            <div className="bg-white rounded-lg shadow-sm p-4 flex-1 overflow-auto custom-scrollbar">
              <h2 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
                <Gauge className="w-5 h-5 mr-2 text-green-600" />
                Analytics
              </h2>
              <AnalyticsDashboard
                selectedDevice={selectedDevice}
                systemStats={systemStats}
              />
            </div>

            {/* Alerts */}
            <div className="bg-white rounded-lg shadow-sm p-4 max-h-[250px] overflow-auto custom-scrollbar">
              <h2 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
                <Bell className="w-5 h-5 mr-2 text-red-600" />
                Alerts
                {systemStats.unacknowledged_alerts > 0 && (
                  <span className="ml-2 bg-red-500 text-white text-xs rounded-full px-2 py-1">
                    {systemStats.unacknowledged_alerts}
                  </span>
                )}
              </h2>
              <AlertPanel
                alerts={alerts}
                role={user?.role}
                username={user?.username || ''}
                onAlertChanged={handleAlertChanged}
                selectedAlertId={selectedAlert?.id || ''}
                onSelectAlert={setSelectedAlert}
              />
            </div>

            <RouteReplayTimeline
              selectedDevice={selectedDevice}
              onReplayPointChange={setReplayPoint}
            />

            <IncidentWorkspace selectedAlert={selectedAlert} />

            {/* Workflow Controls */}
            <div className="bg-white rounded-lg shadow-sm p-4 max-h-[260px] overflow-auto custom-scrollbar">
              <WorkflowPanel role={user?.role} />
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

// Stat Card Component
function StatCard({ icon, label, value, color }) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    red: 'bg-red-50 text-red-600',
  }

  return (
    <div className="bg-white rounded-lg p-3 border border-gray-100">
      <div className="flex items-center space-x-3">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-sm text-gray-500">{label}</p>
        </div>
      </div>
    </div>
  )
}

export default Dashboard

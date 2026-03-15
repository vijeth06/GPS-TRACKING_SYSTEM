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
  MapPin, Activity, AlertTriangle, Truck, Gauge, Bell, ShieldCheck, Route, SearchCheck, Wrench, LayoutGrid, Radar, Siren, Settings2
} from 'lucide-react'
import MapView from '../components/MapView'
import DeviceList from '../components/DeviceList'
import AlertPanel from '../components/AlertPanel'
import AnalyticsDashboard from '../components/AnalyticsDashboard'
import WorkflowPanel from '../components/WorkflowPanel'
import RouteReplayTimeline from '../components/RouteReplayTimeline'
import IncidentWorkspace from '../components/IncidentWorkspace'
import AdvancedOpsPanel from '../components/AdvancedOpsPanel'
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
  const [workspaceTab, setWorkspaceTab] = useState('all')
  const [activeView, setActiveView] = useState('overview')
  const [overviewRailTab, setOverviewRailTab] = useState('devices')

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

        // Track live disconnect / reconnect events
        socketService.socket?.on('disconnect', () => setIsConnected(false))
        socketService.socket?.on('connect',    () => setIsConnected(true))
      } catch (error) {
        console.error('Socket connection failed:', error)
        setIsConnected(false)
      }
    }

    connectSocket()

    return () => {
      socketService.disconnect()
      setIsConnected(false)
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

    setAlerts((prevAlerts) => {
      const prev = prevAlerts.find((a) => a.id === updatedAlert.id)
      const wasUnacked = prev && !prev.is_acknowledged
      const nowAcked = updatedAlert.is_acknowledged

      // Only decrement counter when transitioning from un-acked → acked
      if (wasUnacked && nowAcked) {
        setSystemStats((s) => ({
          ...s,
          unacknowledged_alerts: Math.max(0, s.unacknowledged_alerts - 1),
        }))
      }

      return prevAlerts.map((alert) =>
        alert.id === updatedAlert.id ? { ...alert, ...updatedAlert } : alert
      )
    })
  }, [])

  return (
    <div className="dashboard-shell min-h-screen">
      {/* Header */}
      <header className="px-4 pt-4 md:px-6 md:pt-6">
        <div className="dashboard-header-card">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-amber-500 p-2 rounded-xl shadow-lg shadow-amber-500/30">
                <MapPin className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-extrabold tracking-tight text-white">
                  GPS Tracking System
                </h1>
                <p className="text-sm text-slate-200">
                  Real-Time Fleet Command Center
                </p>
              </div>
            </div>
            
            {/* Connection Status */}
            <div className="flex flex-wrap items-center gap-3 md:gap-4">
              <div className="text-right">
                <p className="text-sm font-medium text-white">{user?.username}</p>
                <p className="text-xs text-slate-300 uppercase tracking-widest">{user?.role}</p>
              </div>
              <div className="flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 backdrop-blur">
                <div
                  className={`w-3 h-3 rounded-full ${
                    isConnected ? 'bg-emerald-400 pulse-animation' : 'bg-rose-500'
                  }`}
                />
                <span className="text-sm text-white">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              <button
                type="button"
                onClick={logout}
                className="text-sm px-3 py-1 rounded-lg bg-white text-slate-800 hover:bg-amber-100 transition-colors"
              >
                Logout
              </button>
            </div>
          </div>

          {/* Stats Bar */}
          <div className="mt-5 grid grid-cols-2 lg:grid-cols-4 gap-3">
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
      <main className="px-4 pb-6 pt-4 md:px-6">
        <div className="panel-card p-2 md:p-3 mb-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
            <PrimaryNavButton
              active={activeView === 'overview'}
              onClick={() => setActiveView('overview')}
              icon={<Radar className="w-4 h-4" />}
              title="Overview"
              subtitle="Map + quick controls"
            />
            <PrimaryNavButton
              active={activeView === 'devices'}
              onClick={() => setActiveView('devices')}
              icon={<Truck className="w-4 h-4" />}
              title="Devices"
              subtitle="Fleet and telemetry"
            />
            <PrimaryNavButton
              active={activeView === 'alerts'}
              onClick={() => setActiveView('alerts')}
              icon={<Siren className="w-4 h-4" />}
              title="Alerts"
              subtitle="Triage and incident"
            />
            <PrimaryNavButton
              active={activeView === 'operations'}
              onClick={() => setActiveView('operations')}
              icon={<Settings2 className="w-4 h-4" />}
              title="Operations"
              subtitle="Workflow and advanced"
            />
          </div>
        </div>

        {activeView === 'overview' && (
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 h-[calc(100vh-290px)] min-h-[680px]">
            <div className="xl:col-span-8 panel-card p-2 overflow-hidden">
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

            <div className="xl:col-span-4 panel-card p-3 overflow-hidden flex flex-col">
              <div className="grid grid-cols-3 gap-2 mb-3">
                <WorkspaceTabButton
                  active={overviewRailTab === 'devices'}
                  onClick={() => setOverviewRailTab('devices')}
                  icon={<Truck className="w-4 h-4" />}
                  label="Devices"
                />
                <WorkspaceTabButton
                  active={overviewRailTab === 'analytics'}
                  onClick={() => setOverviewRailTab('analytics')}
                  icon={<Gauge className="w-4 h-4" />}
                  label="Analytics"
                />
                <WorkspaceTabButton
                  active={overviewRailTab === 'alerts'}
                  onClick={() => setOverviewRailTab('alerts')}
                  icon={<Bell className="w-4 h-4" />}
                  label="Alerts"
                />
              </div>

              <div className="flex-1 overflow-auto custom-scrollbar pr-1">
                {overviewRailTab === 'devices' && (
                  <DeviceList
                    devices={devices}
                    selectedDevice={selectedDevice}
                    onDeviceSelect={handleDeviceSelect}
                  />
                )}
                {overviewRailTab === 'analytics' && (
                  <AnalyticsDashboard
                    selectedDevice={selectedDevice}
                    systemStats={systemStats}
                  />
                )}
                {overviewRailTab === 'alerts' && (
                  <AlertPanel
                    alerts={alerts}
                    role={user?.role}
                    username={user?.username || ''}
                    onAlertChanged={handleAlertChanged}
                    selectedAlertId={selectedAlert?.id || ''}
                    onSelectAlert={(alert) => {
                      setSelectedAlert(alert)
                      setWorkspaceTab('incident')
                      setActiveView('alerts')
                    }}
                  />
                )}
              </div>
            </div>
          </div>
        )}

        {activeView === 'devices' && (
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 h-[calc(100vh-290px)] min-h-[680px]">
            <div className="xl:col-span-4 panel-card p-4 overflow-auto custom-scrollbar">
              <h2 className="panel-title mb-3 flex items-center">
                <Truck className="w-5 h-5 mr-2 text-amber-600" />
                Device Directory
              </h2>
              <DeviceList
                devices={devices}
                selectedDevice={selectedDevice}
                onDeviceSelect={handleDeviceSelect}
              />
            </div>

            <div className="xl:col-span-8 flex flex-col gap-4 overflow-hidden">
              <div className="panel-card p-4 overflow-auto custom-scrollbar">
                <h2 className="panel-title mb-3 flex items-center">
                  <Gauge className="w-5 h-5 mr-2 text-emerald-600" />
                  Telemetry Analytics
                </h2>
                <AnalyticsDashboard
                  selectedDevice={selectedDevice}
                  systemStats={systemStats}
                />
              </div>
              <div className="panel-card p-4 overflow-auto custom-scrollbar">
                <h2 className="panel-title mb-3 flex items-center">
                  <Route className="w-5 h-5 mr-2 text-sky-600" />
                  Route Replay
                </h2>
                <RouteReplayTimeline
                  selectedDevice={selectedDevice}
                  onReplayPointChange={setReplayPoint}
                />
              </div>
            </div>
          </div>
        )}

        {activeView === 'alerts' && (
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 h-[calc(100vh-290px)] min-h-[680px]">
            <div className="xl:col-span-5 panel-card p-4 overflow-auto custom-scrollbar">
              <h2 className="panel-title mb-3 flex items-center">
                <Bell className="w-5 h-5 mr-2 text-rose-600" />
                Alert Feed
                {systemStats.unacknowledged_alerts > 0 && (
                  <span className="ml-2 bg-rose-500 text-white text-xs rounded-full px-2 py-1">
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
                onSelectAlert={(alert) => {
                  setSelectedAlert(alert)
                  setWorkspaceTab('incident')
                }}
              />
            </div>
            <div className="xl:col-span-7 panel-card p-4 overflow-auto custom-scrollbar">
              <h2 className="panel-title mb-3 flex items-center">
                <SearchCheck className="w-5 h-5 mr-2 text-sky-600" />
                Incident Workspace
              </h2>
              <IncidentWorkspace selectedAlert={selectedAlert} />
            </div>
          </div>
        )}

        {activeView === 'operations' && (
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 h-[calc(100vh-290px)] min-h-[680px]">
            <div className="xl:col-span-4 panel-card p-4 overflow-hidden">
              <h2 className="panel-title mb-3 flex items-center">
                <ShieldCheck className="w-5 h-5 mr-2 text-sky-600" />
                Operations Navigation
              </h2>
              <div className="grid grid-cols-2 gap-2 mb-3">
                <WorkspaceTabButton
                  active={workspaceTab === 'all'}
                  onClick={() => setWorkspaceTab('all')}
                  icon={<LayoutGrid className="w-4 h-4" />}
                  label="All"
                />
                <WorkspaceTabButton
                  active={workspaceTab === 'replay'}
                  onClick={() => setWorkspaceTab('replay')}
                  icon={<Route className="w-4 h-4" />}
                  label="Replay"
                />
                <WorkspaceTabButton
                  active={workspaceTab === 'incident'}
                  onClick={() => setWorkspaceTab('incident')}
                  icon={<SearchCheck className="w-4 h-4" />}
                  label="Incident"
                />
                <WorkspaceTabButton
                  active={workspaceTab === 'workflow'}
                  onClick={() => setWorkspaceTab('workflow')}
                  icon={<Wrench className="w-4 h-4" />}
                  label="Workflow"
                />
                <WorkspaceTabButton
                  active={workspaceTab === 'advanced'}
                  onClick={() => setWorkspaceTab('advanced')}
                  icon={<ShieldCheck className="w-4 h-4" />}
                  label="Advanced"
                />
              </div>
              <p className="text-xs text-slate-500">
                Each section is isolated here for smoother operation and lower visual noise.
              </p>
            </div>

            <div className="xl:col-span-8 panel-card p-4 overflow-auto custom-scrollbar">
              {workspaceTab === 'all' && (
                <div className="space-y-3">
                  <RouteReplayTimeline
                    selectedDevice={selectedDevice}
                    onReplayPointChange={setReplayPoint}
                  />
                  <IncidentWorkspace selectedAlert={selectedAlert} />
                  <WorkflowPanel role={user?.role} />
                  <AdvancedOpsPanel role={user?.role} selectedDevice={selectedDevice} />
                </div>
              )}
              {workspaceTab === 'replay' && (
                <RouteReplayTimeline
                  selectedDevice={selectedDevice}
                  onReplayPointChange={setReplayPoint}
                />
              )}
              {workspaceTab === 'incident' && (
                <IncidentWorkspace selectedAlert={selectedAlert} />
              )}
              {workspaceTab === 'workflow' && (
                <WorkflowPanel role={user?.role} />
              )}
              {workspaceTab === 'advanced' && (
                <AdvancedOpsPanel role={user?.role} selectedDevice={selectedDevice} />
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

function PrimaryNavButton({ active, onClick, icon, title, subtitle }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'text-left rounded-xl border px-3 py-2.5 transition-colors',
        active
          ? 'bg-slate-900 text-white border-slate-900'
          : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50',
      ].join(' ')}
    >
      <div className="flex items-center gap-2 text-sm font-semibold">
        {icon}
        <span>{title}</span>
      </div>
      <p className={active ? 'text-[11px] mt-1 text-slate-300' : 'text-[11px] mt-1 text-slate-500'}>{subtitle}</p>
    </button>
  )
}

function WorkspaceTabButton({ active, onClick, icon, label }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'flex items-center justify-center gap-2 rounded-lg px-2 py-2 text-sm font-medium border transition-colors',
        active
          ? 'bg-sky-600 text-white border-sky-600'
          : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100',
      ].join(' ')}
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}

// Stat Card Component
function StatCard({ icon, label, value, color }) {
  const colorClasses = {
    blue: 'bg-sky-50 text-sky-700',
    green: 'bg-emerald-50 text-emerald-700',
    yellow: 'bg-amber-50 text-amber-700',
    red: 'bg-rose-50 text-rose-700',
  }

  return (
    <div className="rounded-xl p-3 bg-white/95 border border-white/80 shadow-[0_10px_20px_rgba(15,23,42,0.08)]">
      <div className="flex items-center space-x-3">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
        <div>
          <p className="text-2xl font-bold text-slate-900 leading-none">{value}</p>
          <p className="text-xs uppercase tracking-wide text-slate-500 mt-1">{label}</p>
        </div>
      </div>
    </div>
  )
}

export default Dashboard

/**
 * AlertPanel Component
 * 
 * Displays alerts feed with ability to acknowledge.
 */

import React from 'react'
import { 
  AlertTriangle, 
  MapPin, 
  Gauge, 
  Clock,
  Check,
  UserCheck,
  ChevronUp,
  CheckCircle2,
} from 'lucide-react'
import { acknowledgeAlert, assignAlert, escalateAlert, resolveAlert } from '../services/api'

// Alert type configurations
const ALERT_CONFIG = {
  stationary_alert: {
    icon: Clock,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-l-yellow-500',
    label: 'Stationary',
  },
  speed_alert: {
    icon: Gauge,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-l-red-500',
    label: 'Speed Alert',
  },
  geofence_alert: {
    icon: MapPin,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-l-purple-500',
    label: 'Geofence',
  },
  default: {
    icon: AlertTriangle,
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    borderColor: 'border-l-gray-500',
    label: 'Alert',
  },
}

// Severity colors
const SEVERITY_CONFIG = {
  low: 'bg-blue-100 text-blue-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
}

function formatTimestamp(timestamp) {
  if (!timestamp) return 'N/A'
  const date = new Date(timestamp)
  const now = new Date()
  const diff = (now - date) / 1000 // seconds

  if (diff < 60) return 'Just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return date.toLocaleDateString()
}

function AlertPanel({ alerts, role = 'viewer', username = '', onAlertChanged, selectedAlertId = '', onSelectAlert }) {
  const [busyId, setBusyId] = React.useState('')
  const [assignees, setAssignees] = React.useState({})
  const [actionError, setActionError] = React.useState('')

  const canOperate = role === 'admin' || role === 'operator'

  const showError = (msg) => {
    setActionError(msg)
    setTimeout(() => setActionError(''), 4000)
  }

  const emitChange = (alert) => {
    if (onAlertChanged) {
      onAlertChanged(alert)
    }
  }

  const handleAcknowledge = async (alertId, e) => {
    e.stopPropagation()
    setBusyId(alertId)
    try {
      const updated = await acknowledgeAlert(alertId)
      emitChange(updated)
    } catch (error) {
      console.error('Error acknowledging alert:', error)
      showError('Failed to acknowledge alert. Check your connection or permissions.')
    } finally {
      setBusyId('')
    }
  }

  const handleAssign = async (alert, e) => {
    e.stopPropagation()
    const assignee = (assignees[alert.id] || '').trim() || username.trim()
    if (!assignee || assignee.length < 2) {
      showError('Enter a name (min 2 characters) in the "Assign to" field.')
      return
    }
    setBusyId(alert.id)
    try {
      const updated = await assignAlert(alert.id, assignee, 'Assigned from alert panel')
      emitChange(updated)
    } catch (error) {
      console.error('Error assigning alert:', error)
      showError('Failed to assign alert. Check your permissions.')
    } finally {
      setBusyId('')
    }
  }

  const handleEscalate = async (alertId, e) => {
    e.stopPropagation()
    setBusyId(alertId)
    try {
      const updated = await escalateAlert(alertId, 'Escalated from alert panel')
      emitChange(updated)
    } catch (error) {
      console.error('Error escalating alert:', error)
      showError('Failed to escalate alert. Check your permissions.')
    } finally {
      setBusyId('')
    }
  }

  const handleResolve = async (alertId, e) => {
    e.stopPropagation()
    setBusyId(alertId)
    try {
      const updated = await resolveAlert(alertId, 'Resolved from alert panel')
      emitChange(updated)
    } catch (error) {
      console.error('Error resolving alert:', error)
      showError('Failed to resolve alert. Check your permissions.')
    } finally {
      setBusyId('')
    }
  }

  if (!alerts || alerts.length === 0) {
    return (
      <div className="text-center text-gray-500 py-4">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No alerts</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {actionError && (
        <div className="px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 font-medium">
          {actionError}
        </div>
      )}
      {alerts.slice(0, 20).map((alert) => {
        const config = ALERT_CONFIG[alert.alert_type] || ALERT_CONFIG.default
        const Icon = config.icon
        const severityClass = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.medium

        return (
          <div
            key={alert.id}
            onClick={() => onSelectAlert && onSelectAlert(alert)}
            className={`
              p-3 rounded-lg border-l-4 transition-all duration-200
              ${config.borderColor} ${config.bgColor}
              ${alert.is_acknowledged ? 'opacity-60' : ''}
              ${selectedAlertId === alert.id ? 'ring-2 ring-blue-500' : ''}
              ${onSelectAlert ? 'cursor-pointer' : ''}
            `}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-2">
                <Icon className={`w-4 h-4 mt-0.5 ${config.color}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="text-xs font-medium text-gray-700">
                      {alert.device_id}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded text-xs ${severityClass}`}>
                      {alert.severity}
                    </span>
                  </div>
                  <p className="text-sm text-gray-800 line-clamp-2">
                    {alert.message}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {formatTimestamp(alert.timestamp)}
                  </p>
                </div>
              </div>

              {/* Acknowledge button */}
              {!alert.is_acknowledged && canOperate && (
                <button
                  onClick={(e) => handleAcknowledge(alert.id, e)}
                  disabled={busyId === alert.id}
                  className="p-1 hover:bg-white rounded transition-colors disabled:opacity-50"
                  title="Acknowledge"
                >
                  <Check className="w-4 h-4 text-green-600" />
                </button>
              )}
              {alert.is_acknowledged && (
                <Check className="w-4 h-4 text-gray-400" />
              )}
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="text-[11px] px-2 py-0.5 rounded bg-gray-100 text-gray-600 uppercase">
                {alert.status || 'triggered'}
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded bg-orange-100 text-orange-700">
                Esc L{alert.escalation_level || 0}
              </span>
              {alert.assigned_to && (
                <span className="text-[11px] px-2 py-0.5 rounded bg-blue-100 text-blue-700">
                  {alert.assigned_to}
                </span>
              )}
            </div>

            {canOperate && alert.status !== 'resolved' && (
              <div className="mt-2 flex flex-wrap gap-2">
                <input
                  value={assignees[alert.id] || ''}
                  onChange={(e) => setAssignees((prev) => ({ ...prev, [alert.id]: e.target.value }))}
                  placeholder="Assign to"
                  className="text-xs px-2 py-1 rounded border border-gray-200 bg-white"
                />
                <button
                  onClick={(e) => handleAssign(alert, e)}
                  disabled={busyId === alert.id}
                  className="text-xs px-2 py-1 rounded bg-blue-600 text-white disabled:opacity-50 flex items-center gap-1"
                >
                  <UserCheck className="w-3 h-3" /> Assign
                </button>
                <button
                  onClick={(e) => handleEscalate(alert.id, e)}
                  disabled={busyId === alert.id}
                  className="text-xs px-2 py-1 rounded bg-amber-600 text-white disabled:opacity-50 flex items-center gap-1"
                >
                  <ChevronUp className="w-3 h-3" /> Escalate
                </button>
                <button
                  onClick={(e) => handleResolve(alert.id, e)}
                  disabled={busyId === alert.id}
                  className="text-xs px-2 py-1 rounded bg-emerald-600 text-white disabled:opacity-50 flex items-center gap-1"
                >
                  <CheckCircle2 className="w-3 h-3" /> Resolve
                </button>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default AlertPanel

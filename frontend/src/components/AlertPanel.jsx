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
  XCircle 
} from 'lucide-react'
import { acknowledgeAlert } from '../services/api'

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

function AlertPanel({ alerts, onAcknowledge }) {
  const handleAcknowledge = async (alertId, e) => {
    e.stopPropagation()
    try {
      await acknowledgeAlert(alertId)
      onAcknowledge(alertId)
    } catch (error) {
      console.error('Error acknowledging alert:', error)
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
      {alerts.slice(0, 20).map((alert) => {
        const config = ALERT_CONFIG[alert.alert_type] || ALERT_CONFIG.default
        const Icon = config.icon
        const severityClass = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.medium

        return (
          <div
            key={alert.id}
            className={`
              p-3 rounded-lg border-l-4 transition-all duration-200
              ${config.borderColor} ${config.bgColor}
              ${alert.is_acknowledged ? 'opacity-60' : ''}
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
              {!alert.is_acknowledged && (
                <button
                  onClick={(e) => handleAcknowledge(alert.id, e)}
                  className="p-1 hover:bg-white rounded transition-colors"
                  title="Acknowledge"
                >
                  <Check className="w-4 h-4 text-green-600" />
                </button>
              )}
              {alert.is_acknowledged && (
                <Check className="w-4 h-4 text-gray-400" />
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default AlertPanel

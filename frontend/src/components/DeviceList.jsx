/**
 * DeviceList Component
 * 
 * Displays a list of tracked devices with their status.
 */

import React from 'react'
import { Truck, Circle } from 'lucide-react'

// Status colors and labels
const STATUS_CONFIG = {
  stationary: { color: 'bg-gray-500', label: 'Stationary' },
  slow: { color: 'bg-yellow-500', label: 'Slow' },
  normal: { color: 'bg-green-500', label: 'Normal' },
  fast: { color: 'bg-red-500', label: 'Fast' },
  offline: { color: 'bg-gray-300', label: 'Offline' },
}

function getDeviceStatus(device) {
  const { latest_location } = device
  if (!latest_location || latest_location.speed === null) {
    return 'offline'
  }
  const speed = latest_location.speed
  if (speed < 5) return 'stationary'
  if (speed < 20) return 'slow'
  if (speed < 60) return 'normal'
  return 'fast'
}

function DeviceList({ devices, selectedDevice, onDeviceSelect }) {
  if (!devices || devices.length === 0) {
    return (
      <div className="text-center text-gray-500 py-4">
        <Truck className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No devices found</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {devices.map((device) => {
        const status = getDeviceStatus(device)
        const statusConfig = STATUS_CONFIG[status]
        const isSelected = selectedDevice?.device_id === device.device_id
        const speed = device.latest_location?.speed

        return (
          <div
            key={device.device_id}
            onClick={() => onDeviceSelect(device)}
            className={`
              p-3 rounded-lg cursor-pointer transition-all duration-200
              ${isSelected 
                ? 'bg-blue-50 border border-blue-200' 
                : 'bg-gray-50 hover:bg-gray-100 border border-transparent'
              }
            `}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                {/* Status indicator */}
                <div className={`w-3 h-3 rounded-full ${statusConfig.color}`} />
                
                {/* Device info */}
                <div>
                  <p className="font-medium text-gray-900 text-sm">
                    {device.device_name || device.device_id}
                  </p>
                  <p className="text-xs text-gray-500">
                    {device.device_id}
                  </p>
                </div>
              </div>

              {/* Speed */}
              <div className="text-right">
                <p className="text-sm font-semibold text-gray-700">
                  {speed !== null && speed !== undefined 
                    ? `${speed.toFixed(1)} km/h` 
                    : 'N/A'
                  }
                </p>
                <p className="text-xs text-gray-500">{statusConfig.label}</p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default DeviceList

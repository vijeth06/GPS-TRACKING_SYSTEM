/**
 * DeviceList Component
 * 
 * Displays a list of tracked devices with their status.
 */

import React from 'react'
import { Truck, Circle } from 'lucide-react'

// Connectivity colors and labels
const CONNECTIVITY_CONFIG = {
  online: { color: 'bg-green-500', label: 'Online' },
  delayed: { color: 'bg-yellow-500', label: 'Delayed' },
  offline: { color: 'bg-gray-300', label: 'Offline' },
}

const MOVEMENT_LABELS = {
  stationary: 'Stationary',
  slow: 'Slow',
  normal: 'Normal',
  fast: 'Fast',
  unknown: 'Unknown',
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
        const connectivity = device.connection_status || 'offline'
        const connectivityConfig = CONNECTIVITY_CONFIG[connectivity] || CONNECTIVITY_CONFIG.offline
        const movementLabel = MOVEMENT_LABELS[device.movement_status || 'unknown'] || 'Unknown'
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
                <div className={`w-3 h-3 rounded-full ${connectivityConfig.color}`} />
                
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
                <p className="text-xs text-gray-500">{connectivityConfig.label} • {movementLabel}</p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default DeviceList

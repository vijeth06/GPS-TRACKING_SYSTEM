/**
 * AnalyticsDashboard Component
 * 
 * Displays analytics data including:
 * - Speed over time chart
 * - Device statistics
 * - Movement summary
 */

import React, { useState, useEffect } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import { Route, Timer, Gauge, TrendingUp } from 'lucide-react'
import { getDeviceAnalytics, getSpeedOverTime } from '../services/api'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

function AnalyticsDashboard({ selectedDevice, systemStats }) {
  const [analytics, setAnalytics] = useState(null)
  const [speedData, setSpeedData] = useState(null)
  const [loading, setLoading] = useState(false)

  // Fetch analytics when device is selected
  useEffect(() => {
    const fetchAnalytics = async () => {
      if (!selectedDevice) {
        setAnalytics(null)
        setSpeedData(null)
        return
      }

      setLoading(true)
      try {
        const now = new Date()
        const startTime = new Date(now.getTime() - 6 * 60 * 60 * 1000) // Last 6 hours

        const [analyticsData, speedOverTime] = await Promise.all([
          getDeviceAnalytics(selectedDevice.device_id, startTime, now),
          getSpeedOverTime(selectedDevice.device_id, startTime, now, 5),
        ])

        setAnalytics(analyticsData)
        setSpeedData(speedOverTime)
      } catch (error) {
        console.error('Error fetching analytics:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchAnalytics()
  }, [selectedDevice])

  // Chart configuration
  const chartData = speedData?.data
    ? {
        labels: speedData.data.map((d) =>
          new Date(d.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })
        ),
        datasets: [
          {
            label: 'Speed (km/h)',
            data: speedData.data.map((d) => d.speed),
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.4,
            pointRadius: 2,
            pointHoverRadius: 5,
          },
        ],
      }
    : null

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      x: {
        display: true,
        grid: {
          display: false,
        },
        ticks: {
          font: {
            size: 10,
          },
          maxRotation: 45,
        },
      },
      y: {
        display: true,
        beginAtZero: true,
        grid: {
          color: '#f3f4f6',
        },
        ticks: {
          font: {
            size: 10,
          },
        },
      },
    },
  }

  // Show system stats if no device selected
  if (!selectedDevice) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-gray-500 mb-4">
          Select a device to view detailed analytics
        </p>
        <div className="grid grid-cols-2 gap-3">
          <StatBox
            icon={<Route className="w-4 h-4" />}
            label="Total Distance"
            value={`${systemStats.total_distance?.toFixed(1) || 0} km`}
            color="blue"
          />
          <StatBox
            icon={<Gauge className="w-4 h-4" />}
            label="Avg Speed"
            value={`${systemStats.average_speed?.toFixed(1) || 0} km/h`}
            color="green"
          />
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-gray-500 text-sm">Loading analytics...</div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Device header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="font-medium text-gray-900">
            {selectedDevice.device_name || selectedDevice.device_id}
          </p>
          <p className="text-xs text-gray-500">{selectedDevice.device_id}</p>
        </div>
        {analytics && (
          <span
            className={`px-2 py-1 rounded-full text-xs font-medium
              ${analytics.current_status === 'stationary' ? 'bg-gray-100 text-gray-700' :
                analytics.current_status === 'slow' ? 'bg-yellow-100 text-yellow-700' :
                analytics.current_status === 'normal' ? 'bg-green-100 text-green-700' :
                'bg-red-100 text-red-700'
              }
            `}
          >
            {analytics.current_status}
          </span>
        )}
      </div>

      {/* Stats grid */}
      {analytics && (
        <div className="grid grid-cols-2 gap-3">
          <StatBox
            icon={<Route className="w-4 h-4" />}
            label="Distance"
            value={`${analytics.total_distance?.toFixed(2) || 0} km`}
            color="blue"
          />
          <StatBox
            icon={<Gauge className="w-4 h-4" />}
            label="Avg Speed"
            value={`${analytics.average_speed?.toFixed(1) || 0} km/h`}
            color="green"
          />
          <StatBox
            icon={<TrendingUp className="w-4 h-4" />}
            label="Max Speed"
            value={`${analytics.max_speed?.toFixed(1) || 0} km/h`}
            color="red"
          />
          <StatBox
            icon={<Timer className="w-4 h-4" />}
            label="Moving"
            value={formatDuration(analytics.moving_time || 0)}
            color="purple"
          />
        </div>
      )}

      {/* Speed chart */}
      {chartData && chartData.labels.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Speed Over Time</h4>
          <div className="h-32">
            <Line data={chartData} options={chartOptions} />
          </div>
        </div>
      )}
    </div>
  )
}

// Helper Components
function StatBox({ icon, label, value, color }) {
  const colorClasses = {
    blue: 'text-blue-600 bg-blue-50',
    green: 'text-green-600 bg-green-50',
    red: 'text-red-600 bg-red-50',
    purple: 'text-purple-600 bg-purple-50',
  }

  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="flex items-center space-x-2 mb-1">
        <div className={`p-1 rounded ${colorClasses[color]}`}>
          {icon}
        </div>
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <p className="text-lg font-semibold text-gray-900">{value}</p>
    </div>
  )
}

// Format duration in seconds to human readable
function formatDuration(seconds) {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  return `${hours}h ${mins}m`
}

export default AnalyticsDashboard

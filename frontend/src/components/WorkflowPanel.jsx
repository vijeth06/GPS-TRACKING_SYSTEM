import React, { useEffect, useState } from 'react'
import {
  getOpsSnapshot,
  getIngestionStatus,
  ingestRawPacket,
  getGeoserverLayers,
  syncGeoserverLayers,
  triggerDemoGeofence,
  triggerDemoStationary,
} from '../services/api'

function WorkflowPanel() {
  const [ops, setOps] = useState(null)
  const [ingest, setIngest] = useState(null)
  const [layers, setLayers] = useState([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  const refresh = async () => {
    try {
      const [opsData, ingestData, layersData] = await Promise.all([
        getOpsSnapshot(),
        getIngestionStatus(),
        getGeoserverLayers(),
      ])
      setOps(opsData)
      setIngest(ingestData)
      setLayers(layersData)
    } catch (error) {
      setMessage(`Error: ${error?.response?.data?.detail || error.message}`)
    }
  }

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, 10000)
    return () => clearInterval(timer)
  }, [])

  const runSampleIngest = async () => {
    setBusy(true)
    setMessage('')
    try {
      const now = new Date()
      const packet = {
        device_id: 'TRK_UI_01',
        latitude: 11.0168,
        longitude: 76.9558,
        timestamp: now.toISOString(),
        speed: 32.4,
        source: 'ui_workflow_panel',
      }
      const result = await ingestRawPacket(packet)
      setMessage(`Ingest accepted=${result.accepted} dedup=${result.deduplicated}`)
      await refresh()
    } catch (error) {
      setMessage(`Ingest failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const runSync = async () => {
    setBusy(true)
    setMessage('')
    try {
      const result = await syncGeoserverLayers()
      setMessage(`GeoServer sync imported ${result.imported_geofences} geofences`)
      await refresh()
    } catch (error) {
      setMessage(`Sync failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const runDemoGeofence = async () => {
    setBusy(true)
    setMessage('')
    try {
      const result = await triggerDemoGeofence()
      setMessage(result.details)
    } catch (error) {
      setMessage(`Demo failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const runDemoStationary = async () => {
    setBusy(true)
    setMessage('')
    try {
      const result = await triggerDemoStationary('TRK101')
      setMessage(result.details)
    } catch (error) {
      setMessage(`Demo failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-800">Workflow Controls</h3>
        <button
          type="button"
          onClick={refresh}
          className="px-2 py-1 rounded bg-gray-100 hover:bg-gray-200"
        >
          Refresh
        </button>
      </div>

      {ops && (
        <div className="grid grid-cols-2 gap-2">
          <MiniStat label="Online" value={ops.online_devices} />
          <MiniStat label="Delayed" value={ops.delayed_devices} />
          <MiniStat label="Packets/min" value={ops.packets_last_minute} />
          <MiniStat label="Err Rate" value={ops.packet_error_rate} />
        </div>
      )}

      {ingest && (
        <div className="p-2 rounded border border-gray-200 bg-gray-50">
          <p>Ingestion Queue: {ingest.queue_size}</p>
          <p>Processed: {ingest.processed_count}</p>
          <p>Dedup: {ingest.dedup_count}</p>
          <p>Worker: {ingest.worker_running ? 'running' : 'stopped'}</p>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={runSampleIngest}
          className="px-2 py-1 rounded bg-blue-600 text-white disabled:opacity-60"
        >
          Test Ingest
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={runSync}
          className="px-2 py-1 rounded bg-purple-600 text-white disabled:opacity-60"
        >
          Sync GeoServer
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={runDemoGeofence}
          className="px-2 py-1 rounded bg-amber-600 text-white disabled:opacity-60"
        >
          Demo Geofence
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={runDemoStationary}
          className="px-2 py-1 rounded bg-emerald-600 text-white disabled:opacity-60"
        >
          Demo Stationary
        </button>
      </div>

      <div className="p-2 rounded border border-gray-100 bg-white">
        <p className="font-medium text-gray-700">GeoServer Layers</p>
        {layers.length === 0 && <p className="text-gray-500">No layers configured</p>}
        {layers.map((layer) => (
          <p key={layer.layer_name} className="text-gray-700">
            {layer.layer_name} (features: {layer.feature_count})
          </p>
        ))}
      </div>

      {message && <p className="text-xs text-gray-600">{message}</p>}
    </div>
  )
}

function MiniStat({ label, value }) {
  return (
    <div className="rounded border border-gray-200 bg-white px-2 py-1">
      <p className="text-gray-500 text-xs">{label}</p>
      <p className="font-semibold text-gray-900">{value}</p>
    </div>
  )
}

export default WorkflowPanel

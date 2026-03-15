import React, { useEffect, useState } from 'react'
import {
  getOpsSnapshot,
  getIngestionStatus,
  onboardDevice,
  rotateDeviceCredential,
  getDeviceCredentialStatus,
  getGeoserverLayers,
  getGeoserverConfig,
  updateGeoserverLayers,
  clearGeoserverCache,
  syncGeoserverLayers,
  getRetentionStatus,
  runRetentionNow,
} from '../services/api'

function WorkflowPanel({ role = 'viewer' }) {
  const [ops, setOps] = useState(null)
  const [ingest, setIngest] = useState(null)
  const [layers, setLayers] = useState([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [onboardDeviceId, setOnboardDeviceId] = useState('TRK_UI_01')
  const [onboardName, setOnboardName] = useState('Fleet Tracker')
  const [onboardType, setOnboardType] = useState('vehicle')
  const [issuedApiKey, setIssuedApiKey] = useState('')
  const [credentialStatus, setCredentialStatus] = useState(null)
  const [geoserverConfig, setGeoserverConfig] = useState(null)
  const [layerInput, setLayerInput] = useState('')
  const [retentionStatus, setRetentionStatus] = useState(null)
  const canOperate = role === 'admin' || role === 'operator'
  const isAdmin = role === 'admin'

  const layerInputDirty = React.useRef(false)

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
      const [cfg, retention] = await Promise.all([getGeoserverConfig(), getRetentionStatus()])
      setGeoserverConfig(cfg)
      if (!layerInputDirty.current) {
        setLayerInput((cfg.layer_names || []).join(', '))
      }
      setRetentionStatus(retention)
    } catch (error) {
      setMessage(`Error: ${error?.response?.data?.detail || error.message}`)
    }
  }

  const refreshCredentialStatus = async (deviceId) => {
    if (!deviceId) {
      setCredentialStatus(null)
      return
    }
    try {
      const status = await getDeviceCredentialStatus(deviceId)
      setCredentialStatus(status)
    } catch {
      setCredentialStatus(null)
    }
  }

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, 10000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    refreshCredentialStatus(onboardDeviceId)
  }, [onboardDeviceId])

  const runOnboard = async () => {
    setBusy(true)
    setMessage('')
    try {
      const result = await onboardDevice({
        device_id: onboardDeviceId,
        device_name: onboardName,
        device_type: onboardType,
      })
      setIssuedApiKey(result.api_key)
      setMessage(
        `${result.created ? 'Created' : 'Updated'} ${result.device_id}. Save API key now; it is only shown once.`
      )
      await refreshCredentialStatus(onboardDeviceId)
      await refresh()
    } catch (error) {
      setMessage(`Onboarding failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const runRotateKey = async () => {
    setBusy(true)
    setMessage('')
    try {
      const result = await rotateDeviceCredential(onboardDeviceId)
      setIssuedApiKey(result.api_key)
      setMessage(`Rotated API key for ${result.device_id}. Save the new key now.`)
      await refreshCredentialStatus(onboardDeviceId)
    } catch (error) {
      setMessage(`Rotate failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const runDeviceKeyIngest = async () => {
    setBusy(true)
    setMessage('')
    try {
      if (!issuedApiKey) {
        setMessage('No issued key available. Onboard or rotate device first.')
        return
      }
      const now = new Date()
      const packet = {
        device_id: onboardDeviceId,
        latitude: 11.0182,
        longitude: 76.9591,
        timestamp: now.toISOString(),
        speed: 28.7,
        source: 'ui_device_key_test',
      }
      const result = await ingestRawPacket(packet, { deviceKey: issuedApiKey })
      setMessage(`Device-key ingest accepted=${result.accepted} dedup=${result.deduplicated}`)
      await refresh()
      await refreshCredentialStatus(onboardDeviceId)
    } catch (error) {
      setMessage(`Device-key ingest failed: ${error?.response?.data?.detail || error.message}`)
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

  const saveLayers = async () => {
    setBusy(true)
    setMessage('')
    try {
      const layerNames = layerInput
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean)
      const updated = await updateGeoserverLayers(layerNames)
      setGeoserverConfig(updated)
      setMessage(`Saved ${updated.layer_names.length} GeoServer layers`)
      await refresh()
    } catch (error) {
      setMessage(`Save layers failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const purgeGeoserverCache = async () => {
    setBusy(true)
    setMessage('')
    try {
      const result = await clearGeoserverCache()
      setMessage(`Cleared GeoServer cache: ${result.deleted} items`)
      await refresh()
    } catch (error) {
      setMessage(`Cache clear failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const runRetention = async () => {
    setBusy(true)
    setMessage('')
    try {
      const result = await runRetentionNow()
      setMessage(
        `Retention archived gps=${result.archived_gps}, alerts=${result.archived_alerts}, packets=${result.archived_packets}`
      )
      await refresh()
    } catch (error) {
      setMessage(`Retention run failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-800">Workflow Controls</h3>
        <span className="text-xs px-2 py-1 rounded bg-slate-100 text-slate-600 uppercase">{role}</span>
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

      <div className="p-2 rounded border border-sky-200 bg-sky-50 space-y-2">
        <p className="font-medium text-sky-900">Device Onboarding</p>
        <div className="grid grid-cols-1 gap-2">
          <input
            value={onboardDeviceId}
            onChange={(e) => setOnboardDeviceId(e.target.value)}
            placeholder="Device ID"
            className="px-2 py-1 rounded border border-sky-200 bg-white"
          />
          <input
            value={onboardName}
            onChange={(e) => setOnboardName(e.target.value)}
            placeholder="Device Name"
            className="px-2 py-1 rounded border border-sky-200 bg-white"
          />
          <input
            value={onboardType}
            onChange={(e) => setOnboardType(e.target.value)}
            placeholder="Type (vehicle/person/asset/drone)"
            className="px-2 py-1 rounded border border-sky-200 bg-white"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy || !canOperate}
            onClick={runOnboard}
            className="px-2 py-1 rounded bg-sky-700 text-white disabled:opacity-60"
          >
            Onboard Device
          </button>
          <button
            type="button"
            disabled={busy || !canOperate || !onboardDeviceId}
            onClick={runRotateKey}
            className="px-2 py-1 rounded bg-sky-600 text-white disabled:opacity-60"
          >
            Rotate Key
          </button>
          <button
            type="button"
            disabled={busy || !canOperate || !issuedApiKey}
            onClick={runDeviceKeyIngest}
            className="px-2 py-1 rounded bg-indigo-600 text-white disabled:opacity-60"
          >
            Test Device-Key Ingest
          </button>
        </div>
        {credentialStatus && (
          <p className="text-xs text-sky-900">
            Credential active: {credentialStatus.credential_active ? 'yes' : 'no'}
            {credentialStatus.rotated_at ? ` | rotated: ${new Date(credentialStatus.rotated_at).toLocaleString()}` : ''}
          </p>
        )}
        {issuedApiKey && (
          <div className="rounded border border-amber-200 bg-amber-50 p-2">
            <p className="text-xs font-semibold text-amber-900">Issued API Key (shown once)</p>
            <p className="font-mono text-xs text-amber-900 break-all">{issuedApiKey}</p>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy || !isAdmin}
          onClick={runSync}
          className="px-2 py-1 rounded bg-purple-600 text-white disabled:opacity-60"
        >
          Sync GeoServer
        </button>
      </div>

      <div className="p-2 rounded border border-gray-100 bg-white">
        <p className="font-medium text-gray-700">GeoServer Layers</p>
        {geoserverConfig && (
          <p className="text-xs text-gray-500 mb-1">
            WFS Reachable: {geoserverConfig.wfs_reachable === null ? 'unknown' : geoserverConfig.wfs_reachable ? 'yes' : 'no'}
          </p>
        )}
        {layers.length === 0 && <p className="text-gray-500">No layers configured</p>}
        {layers.map((layer) => (
          <p key={layer.layer_name} className="text-gray-700">
            {layer.layer_name} (features: {layer.feature_count})
          </p>
        ))}
        <div className="mt-2 space-y-2">
          <input
            value={layerInput}
            onChange={(e) => {
              layerInputDirty.current = true
              setLayerInput(e.target.value)
            }}
            onBlur={() => { layerInputDirty.current = false }}
            placeholder="layer1, layer2"
            className="w-full px-2 py-1 rounded border border-gray-200"
          />
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy || !isAdmin}
              onClick={saveLayers}
              className="px-2 py-1 rounded bg-indigo-600 text-white disabled:opacity-60"
            >
              Save Layers
            </button>
            <button
              type="button"
              disabled={busy || !isAdmin}
              onClick={purgeGeoserverCache}
              className="px-2 py-1 rounded bg-gray-700 text-white disabled:opacity-60"
            >
              Clear Cache
            </button>
          </div>
        </div>
      </div>

      <div className="p-2 rounded border border-rose-100 bg-rose-50">
        <p className="font-medium text-rose-900">Retention & Archive</p>
        {retentionStatus && (
          <p className="text-xs text-rose-800">
            Enabled: {retentionStatus.enabled ? 'yes' : 'no'} | Interval: {retentionStatus.interval_minutes} min | Cutoff: {retentionStatus.cutoff_days} days
          </p>
        )}
        <button
          type="button"
          disabled={busy || !isAdmin}
          onClick={runRetention}
          className="mt-2 px-2 py-1 rounded bg-rose-600 text-white disabled:opacity-60"
        >
          Run Retention Now
        </button>
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
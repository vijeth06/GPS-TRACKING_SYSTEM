import React, { useEffect, useMemo, useState } from 'react'
import {
  onboardDevice,
  updateDevice,
  deleteDevice,
  rotateDeviceCredential,
} from '../services/api'

const STATUS_OPTIONS = ['active', 'inactive', 'maintenance']
const TYPE_OPTIONS = ['vehicle', 'person', 'asset', 'drone']

function DeviceManagementPanel({
  devices,
  selectedDevice,
  onDeviceSelect,
  onDevicesChanged,
  role = 'viewer',
}) {
  const canOperate = role === 'admin' || role === 'operator'
  const isAdmin = role === 'admin'

  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [issuedApiKey, setIssuedApiKey] = useState('')

  const [createForm, setCreateForm] = useState({
    device_id: '',
    device_name: '',
    device_type: 'vehicle',
  })

  const [editForm, setEditForm] = useState({
    device_name: '',
    device_type: 'vehicle',
    status: 'active',
  })

  useEffect(() => {
    setEditForm({
      device_name: selectedDevice?.device_name || '',
      device_type: selectedDevice?.device_type || 'vehicle',
      status: selectedDevice?.status || 'active',
    })
  }, [selectedDevice?.device_id, selectedDevice?.device_name, selectedDevice?.device_type, selectedDevice?.status])

  const selectedDeviceLabel = useMemo(() => {
    if (!selectedDevice) return 'No device selected'
    return `${selectedDevice.device_name || selectedDevice.device_id} (${selectedDevice.device_id})`
  }, [selectedDevice])

  const handleCreate = async () => {
    if (!createForm.device_id.trim()) {
      setMessage('Device ID is required.')
      return
    }
    try {
      setBusy(true)
      setMessage('')
      const result = await onboardDevice({
        device_id: createForm.device_id.trim(),
        device_name: createForm.device_name.trim() || null,
        device_type: createForm.device_type,
      })
      setIssuedApiKey(result.api_key || '')
      setMessage(`Device ${result.device_id} created and credential issued.`)
      setCreateForm({ device_id: '', device_name: '', device_type: 'vehicle' })
      await onDevicesChanged?.(result.device_id)
    } catch (error) {
      setMessage(`Create failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const handleUpdate = async () => {
    if (!selectedDevice?.device_id) {
      setMessage('Select a device first.')
      return
    }
    try {
      setBusy(true)
      setMessage('')
      await updateDevice(selectedDevice.device_id, {
        device_name: editForm.device_name,
        device_type: editForm.device_type,
        status: editForm.status,
      })
      setMessage(`Updated ${selectedDevice.device_id}.`)
      await onDevicesChanged?.(selectedDevice.device_id)
    } catch (error) {
      setMessage(`Update failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const handleRotateKey = async () => {
    if (!selectedDevice?.device_id) {
      setMessage('Select a device first.')
      return
    }
    try {
      setBusy(true)
      setMessage('')
      const result = await rotateDeviceCredential(selectedDevice.device_id)
      setIssuedApiKey(result.api_key || '')
      setMessage(`Rotated API key for ${selectedDevice.device_id}.`)
      await onDevicesChanged?.(selectedDevice.device_id)
    } catch (error) {
      setMessage(`Rotate key failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const handleDelete = async () => {
    if (!selectedDevice?.device_id) {
      setMessage('Select a device first.')
      return
    }
    const confirmed = window.confirm(`Delete ${selectedDevice.device_id} and its related telemetry?`)
    if (!confirmed) return

    try {
      setBusy(true)
      setMessage('')
      const result = await deleteDevice(selectedDevice.device_id)
      setIssuedApiKey('')
      setMessage(`Deleted ${result.device_id}. Removed ${result.deleted_locations} gps points and ${result.deleted_alerts} alerts.`)
      await onDevicesChanged?.(null)
    } catch (error) {
      setMessage(`Delete failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Add New Device</h3>
            <p className="text-xs text-slate-500">Create a device record and issue its API key once.</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <input
            value={createForm.device_id}
            onChange={(e) => setCreateForm((prev) => ({ ...prev, device_id: e.target.value }))}
            placeholder="Device ID"
            className="px-3 py-2 rounded-lg border border-slate-200 bg-white"
          />
          <input
            value={createForm.device_name}
            onChange={(e) => setCreateForm((prev) => ({ ...prev, device_name: e.target.value }))}
            placeholder="Device name"
            className="px-3 py-2 rounded-lg border border-slate-200 bg-white"
          />
          <select
            value={createForm.device_type}
            onChange={(e) => setCreateForm((prev) => ({ ...prev, device_type: e.target.value }))}
            className="px-3 py-2 rounded-lg border border-slate-200 bg-white"
          >
            {TYPE_OPTIONS.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </div>
        <button
          type="button"
          disabled={busy || !canOperate}
          onClick={handleCreate}
          className="mt-3 px-3 py-2 rounded-lg bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-60"
        >
          Create Device
        </button>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-slate-900">Manage Device</h3>
          <p className="text-xs text-slate-500">Selected: {selectedDeviceLabel}</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] gap-4">
          <div className="space-y-2 max-h-[420px] overflow-auto custom-scrollbar pr-1">
            {devices.length === 0 && (
              <p className="text-sm text-slate-500">No devices available.</p>
            )}
            {devices.map((device) => {
              const selected = selectedDevice?.device_id === device.device_id
              return (
                <button
                  key={device.device_id}
                  type="button"
                  onClick={() => onDeviceSelect?.(device)}
                  className={[
                    'w-full text-left rounded-xl border px-3 py-2 transition-colors',
                    selected
                      ? 'border-sky-500 bg-sky-50'
                      : 'border-slate-200 bg-slate-50 hover:bg-slate-100',
                  ].join(' ')}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{device.device_name || device.device_id}</p>
                      <p className="text-xs text-slate-500">{device.device_id} • {device.device_type}</p>
                    </div>
                    <span className="text-[11px] uppercase tracking-wide text-slate-600">{device.status}</span>
                  </div>
                </button>
              )
            })}
          </div>

          <div className="space-y-3">
            <input
              value={editForm.device_name}
              onChange={(e) => setEditForm((prev) => ({ ...prev, device_name: e.target.value }))}
              placeholder="Device name"
              disabled={!selectedDevice}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white disabled:bg-slate-100"
            />
            <select
              value={editForm.device_type}
              onChange={(e) => setEditForm((prev) => ({ ...prev, device_type: e.target.value }))}
              disabled={!selectedDevice}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white disabled:bg-slate-100"
            >
              {TYPE_OPTIONS.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
            <select
              value={editForm.status}
              onChange={(e) => setEditForm((prev) => ({ ...prev, status: e.target.value }))}
              disabled={!selectedDevice}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white disabled:bg-slate-100"
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busy || !canOperate || !selectedDevice}
                onClick={handleUpdate}
                className="px-3 py-2 rounded-lg bg-sky-700 text-white hover:bg-sky-800 disabled:opacity-60"
              >
                Save Changes
              </button>
              <button
                type="button"
                disabled={busy || !canOperate || !selectedDevice}
                onClick={handleRotateKey}
                className="px-3 py-2 rounded-lg bg-indigo-700 text-white hover:bg-indigo-800 disabled:opacity-60"
              >
                Rotate API Key
              </button>
              <button
                type="button"
                disabled={busy || !isAdmin || !selectedDevice}
                onClick={handleDelete}
                className="px-3 py-2 rounded-lg bg-rose-700 text-white hover:bg-rose-800 disabled:opacity-60"
              >
                Delete Device
              </button>
            </div>

            {issuedApiKey && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                <p className="text-xs font-semibold text-amber-900">Issued API Key</p>
                <p className="mt-1 break-all font-mono text-xs text-amber-900">{issuedApiKey}</p>
              </div>
            )}
          </div>
        </div>
      </section>

      {message && (
        <p className="rounded-lg bg-slate-100 px-3 py-2 text-xs text-slate-600">{message}</p>
      )}
    </div>
  )
}

export default DeviceManagementPanel
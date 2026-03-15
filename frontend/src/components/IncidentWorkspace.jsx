import React, { useEffect, useState } from 'react'
import { Search, ShieldAlert } from 'lucide-react'
import { getIncidentWorkspace, getOpenIncidents } from '../services/api'

function IncidentWorkspace({ selectedAlert }) {
  const [workspace, setWorkspace] = useState(null)
  const [incidentId, setIncidentId] = useState('')
  const [openIncidents, setOpenIncidents] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const loadOpen = async () => {
      try {
        const data = await getOpenIncidents(10)
        setOpenIncidents(data)
      } catch {
        setOpenIncidents([])
      }
    }
    loadOpen()
  }, [])

  useEffect(() => {
    if (selectedAlert?.id) {
      setIncidentId(selectedAlert.id)
    }
  }, [selectedAlert?.id])

  const loadWorkspace = async (idToLoad) => {
    if (!idToLoad) return
    setLoading(true)
    try {
      const data = await getIncidentWorkspace(idToLoad)
      setWorkspace(data)
    } catch {
      setWorkspace(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-red-600" /> Incident Workspace
        </h3>
      </div>

      <div className="flex gap-2">
        <input
          value={incidentId}
          onChange={(e) => setIncidentId(e.target.value)}
          placeholder="Alert ID"
          className="flex-1 px-2 py-1 border border-gray-200 rounded"
        />
        <button
          type="button"
          onClick={() => loadWorkspace(incidentId)}
          className="px-2 py-1 rounded bg-red-600 text-white hover:bg-red-700"
        >
          <Search className="w-4 h-4" />
        </button>
      </div>

      {openIncidents.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-1">Open incidents</p>
          <div className="flex flex-wrap gap-1">
            {openIncidents.slice(0, 6).map((it) => (
              <button
                key={it.id}
                type="button"
                onClick={() => {
                  setIncidentId(it.id)
                  loadWorkspace(it.id)
                }}
                className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200"
              >
                {it.device_id}
              </button>
            ))}
          </div>
        </div>
      )}

      {loading && <p className="text-sm text-gray-500">Loading workspace...</p>}

      {workspace && (
        <div className="space-y-2 text-xs">
          <p className="text-gray-700">{workspace.investigation_summary}</p>
          <div className="grid grid-cols-2 gap-2">
            <MiniStat label="Device" value={workspace.alert.device_id} />
            <MiniStat label="Severity" value={workspace.alert.severity} />
            <MiniStat label="Related Alerts" value={workspace.related_alerts.length} />
            <MiniStat label="Trail Points" value={workspace.recent_trail.points.length} />
          </div>
          <div className="p-2 rounded bg-gray-50 border border-gray-100">
            <p className="font-medium text-gray-700">Latest related alerts</p>
            {workspace.related_alerts.slice(0, 3).map((a) => (
              <p key={a.id} className="text-gray-600">
                {a.alert_type} [{a.severity}]
              </p>
            ))}
            {workspace.related_alerts.length === 0 && <p className="text-gray-500">No related alerts</p>}
          </div>
        </div>
      )}
    </div>
  )
}

function MiniStat({ label, value }) {
  return (
    <div className="rounded border border-gray-200 p-2 bg-white">
      <p className="text-gray-500">{label}</p>
      <p className="font-semibold text-gray-900">{value}</p>
    </div>
  )
}

export default IncidentWorkspace

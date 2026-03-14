import React, { useEffect, useState } from 'react'
import {
  getNotificationChannels,
  saveNotificationChannel,
  testNotificationChannel,
  getAutomationRules,
  createAutomationRule,
  getRoutePlans,
  createRoutePlan,
  getReportingSummary,
  getGovernanceSettings,
  updateGovernanceSettings,
  getAnomalyInsight,
  getAdminUsers,
  createAdminUser,
  getTeams,
  createTeam,
} from '../services/api'

function AdvancedOpsPanel({ role = 'viewer', selectedDevice }) {
  const isAdmin = role === 'admin'
  const canOperate = role === 'admin' || role === 'operator'
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  const [channels, setChannels] = useState([])
  const [rules, setRules] = useState([])
  const [routePlans, setRoutePlans] = useState([])
  const [reporting, setReporting] = useState(null)
  const [governance, setGovernance] = useState(null)
  const [anomaly, setAnomaly] = useState(null)
  const [users, setUsers] = useState([])
  const [teams, setTeams] = useState([])

  const [channelName, setChannelName] = useState('Primary Slack')
  const [channelType, setChannelType] = useState('slack')
  const [channelRecipient, setChannelRecipient] = useState('#fleet-alerts')

  const [ruleName, setRuleName] = useState('Escalate critical anomalies')
  const [routeName, setRouteName] = useState('TRK101 City Loop')

  const [newUsername, setNewUsername] = useState('ops_lead')
  const [newPassword, setNewPassword] = useState('ops123')
  const [teamName, setTeamName] = useState('Ops Alpha')

  const refreshAll = async () => {
    try {
      setBusy(true)
      setMessage('')
      const [
        channelData,
        ruleData,
        routeData,
        reportData,
        governanceData,
        userData,
        teamData,
      ] = await Promise.all([
        getNotificationChannels(),
        getAutomationRules(),
        getRoutePlans(),
        getReportingSummary(24),
        getGovernanceSettings(),
        isAdmin ? getAdminUsers() : Promise.resolve([]),
        canOperate ? getTeams() : Promise.resolve([]),
      ])
      setChannels(channelData)
      setRules(ruleData)
      setRoutePlans(routeData)
      setReporting(reportData)
      setGovernance(governanceData)
      setUsers(userData)
      setTeams(teamData)

      if (selectedDevice?.device_id) {
        const speed = selectedDevice?.latest_location?.speed || 0
        const insight = await getAnomalyInsight(selectedDevice.device_id, speed)
        setAnomaly(insight)
      } else {
        setAnomaly(null)
      }
    } catch (error) {
      setMessage(`Error: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    refreshAll()
  }, [selectedDevice?.device_id])

  const onSaveChannel = async () => {
    try {
      setBusy(true)
      const saved = await saveNotificationChannel({
        name: channelName,
        channel_type: channelType,
        enabled: true,
        recipient: channelRecipient,
        severity_filter: ['high', 'critical'],
      })
      await refreshAll()
      const result = await testNotificationChannel(saved.id, {
        message: 'Test signal from Advanced Ops panel',
        severity: 'high',
      })
      setMessage(result.details)
    } catch (error) {
      setMessage(`Channel failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const onCreateRule = async () => {
    try {
      setBusy(true)
      await createAutomationRule({
        name: ruleName,
        description: 'Auto action for severe movement anomalies',
        event_type: 'gps_point',
        enabled: true,
        priority: 10,
        conditions: [{ field: 'anomaly_score', op: 'gt', value: '0.8' }],
        actions: [{ action_type: 'notify', target: 'high_priority_channel', payload: { mode: 'instant' } }],
      })
      await refreshAll()
      setMessage('Automation rule created')
    } catch (error) {
      setMessage(`Rule failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const onCreateRoute = async () => {
    try {
      setBusy(true)
      const deviceId = selectedDevice?.device_id || 'TRK101'
      await createRoutePlan({
        route_name: routeName,
        device_id: deviceId,
        deviation_threshold_m: 250,
        active: true,
        waypoints: [
          { lat: 11.0168, lng: 76.9558, sequence: 1 },
          { lat: 11.0182, lng: 76.9591, sequence: 2 },
          { lat: 11.0201, lng: 76.9622, sequence: 3 },
        ],
      })
      await refreshAll()
      setMessage(`Route plan created for ${deviceId}`)
    } catch (error) {
      setMessage(`Route failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const onCreateUser = async () => {
    if (!isAdmin) return
    try {
      setBusy(true)
      await createAdminUser({
        username: newUsername,
        password: newPassword,
        full_name: 'Operations Lead',
        role: 'operator',
        is_active: true,
      })
      await refreshAll()
      setMessage(`User ${newUsername} created`)
    } catch (error) {
      setMessage(`User failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const onCreateTeam = async () => {
    if (!canOperate) return
    try {
      setBusy(true)
      await createTeam({
        team_name: teamName,
        lead_username: users?.[0]?.username || 'admin',
        members: users.slice(0, 2).map((u) => u.username),
        on_call: true,
      })
      await refreshAll()
      setMessage(`Team ${teamName} created`)
    } catch (error) {
      setMessage(`Team failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const onTightenGovernance = async () => {
    if (!isAdmin || !governance) return
    try {
      setBusy(true)
      await updateGovernanceSettings({
        ...governance,
        mask_device_identifier: true,
        mask_precision_decimals: 3,
        export_requires_admin: true,
      })
      await refreshAll()
      setMessage('Governance policy updated')
    } catch (error) {
      setMessage(`Governance failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3 text-xs border border-gray-200 rounded-lg p-3 bg-gray-50">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-800">Advanced Operations</h3>
        <button
          type="button"
          disabled={busy}
          onClick={refreshAll}
          className="px-2 py-1 rounded bg-white border border-gray-200 disabled:opacity-60"
        >
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 gap-2">
        <div className="p-2 rounded border border-indigo-200 bg-indigo-50">
          <p className="font-medium text-indigo-900">Notifications</p>
          <p>Channels: {channels.length}</p>
          <div className="mt-1 grid grid-cols-1 gap-1">
            <input value={channelName} onChange={(e) => setChannelName(e.target.value)} className="px-2 py-1 rounded border" />
            <input value={channelType} onChange={(e) => setChannelType(e.target.value)} className="px-2 py-1 rounded border" />
            <input value={channelRecipient} onChange={(e) => setChannelRecipient(e.target.value)} className="px-2 py-1 rounded border" />
          </div>
          <button type="button" disabled={busy || !canOperate} onClick={onSaveChannel} className="mt-1 px-2 py-1 rounded bg-indigo-600 text-white disabled:opacity-60">Save & Test</button>
        </div>

        <div className="p-2 rounded border border-cyan-200 bg-cyan-50">
          <p className="font-medium text-cyan-900">Rule Engine</p>
          <p>Rules: {rules.length}</p>
          <input value={ruleName} onChange={(e) => setRuleName(e.target.value)} className="mt-1 w-full px-2 py-1 rounded border" />
          <button type="button" disabled={busy || !canOperate} onClick={onCreateRule} className="mt-1 px-2 py-1 rounded bg-cyan-700 text-white disabled:opacity-60">Add Rule</button>
        </div>

        <div className="p-2 rounded border border-emerald-200 bg-emerald-50">
          <p className="font-medium text-emerald-900">Route Deviation</p>
          <p>Route plans: {routePlans.length}</p>
          <input value={routeName} onChange={(e) => setRouteName(e.target.value)} className="mt-1 w-full px-2 py-1 rounded border" />
          <button type="button" disabled={busy || !canOperate} onClick={onCreateRoute} className="mt-1 px-2 py-1 rounded bg-emerald-700 text-white disabled:opacity-60">Create Route</button>
        </div>

        <div className="p-2 rounded border border-amber-200 bg-amber-50">
          <p className="font-medium text-amber-900">Reporting & Intelligence</p>
          {reporting && <p>24h alerts: {reporting.total_alerts} | resolved: {reporting.resolved_alerts} | avg speed: {reporting.avg_speed}</p>}
          {anomaly && <p>Anomaly for {anomaly.device_id}: score {anomaly.anomaly_score} ({anomaly.reason})</p>}
        </div>

        {(isAdmin || canOperate) && (
          <div className="p-2 rounded border border-rose-200 bg-rose-50">
            <p className="font-medium text-rose-900">Teams & Users</p>
            <p>Users: {users.length} | Teams: {teams.length}</p>
            {isAdmin && (
              <div className="mt-1 grid grid-cols-1 gap-1">
                <input value={newUsername} onChange={(e) => setNewUsername(e.target.value)} className="px-2 py-1 rounded border" />
                <input value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="px-2 py-1 rounded border" />
                <button type="button" disabled={busy} onClick={onCreateUser} className="px-2 py-1 rounded bg-rose-700 text-white disabled:opacity-60">Create User</button>
              </div>
            )}
            <div className="mt-1 grid grid-cols-1 gap-1">
              <input value={teamName} onChange={(e) => setTeamName(e.target.value)} className="px-2 py-1 rounded border" />
              <button type="button" disabled={busy || !canOperate} onClick={onCreateTeam} className="px-2 py-1 rounded bg-rose-600 text-white disabled:opacity-60">Create Team</button>
            </div>
          </div>
        )}

        {isAdmin && governance && (
          <div className="p-2 rounded border border-slate-300 bg-slate-100">
            <p className="font-medium text-slate-900">Data Governance</p>
            <p>Mask IDs: {governance.mask_device_identifier ? 'yes' : 'no'} | Precision: {governance.mask_precision_decimals}</p>
            <button type="button" disabled={busy} onClick={onTightenGovernance} className="mt-1 px-2 py-1 rounded bg-slate-800 text-white disabled:opacity-60">Tighten Policy</button>
          </div>
        )}
      </div>

      {message && <p className="text-gray-600">{message}</p>}
    </div>
  )
}

export default AdvancedOpsPanel

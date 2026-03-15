import React, { useEffect, useState } from 'react'
import {
  getStreamListenerStatus,
  startStreamListener,
  stopStreamListener,
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
  const [streamStatus, setStreamStatus] = useState(null)
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
  const [streamProtocol, setStreamProtocol] = useState('udp')
  const [streamPort, setStreamPort] = useState(9100)
  const [datasetProfile, setDatasetProfile] = useState('flexible')

  const refreshAll = async (showBusy = false) => {
    try {
      if (showBusy) setBusy(true)
      setMessage('')
      const [
        streamData,
        channelData,
        ruleData,
        routeData,
        reportData,
        governanceData,
        userData,
        teamData,
      ] = await Promise.all([
        getStreamListenerStatus(),
        getNotificationChannels(),
        getAutomationRules(),
        getRoutePlans(),
        getReportingSummary(24),
        getGovernanceSettings(),
        isAdmin ? getAdminUsers() : Promise.resolve([]),
        canOperate ? getTeams() : Promise.resolve([]),
      ])
      setStreamStatus(streamData)
      if (streamData?.protocol) setStreamProtocol(streamData.protocol)
      if (streamData?.port) setStreamPort(streamData.port)
      if (streamData?.dataset_profile) setDatasetProfile(streamData.dataset_profile)
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

  const onStartStream = async () => {
    try {
      setBusy(true)
      const status = await startStreamListener({
        protocol: streamProtocol,
        port: Number(streamPort),
        dataset_profile: datasetProfile,
      })
      setStreamStatus(status)
      setMessage(`Stream started (${status.protocol.toUpperCase()}:${status.port}) with ${status.dataset_profile} profile`)
    } catch (error) {
      setMessage(`Stream start failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const onStopStream = async () => {
    try {
      setBusy(true)
      const status = await stopStreamListener()
      setStreamStatus(status)
      setMessage('Stream stopped')
    } catch (error) {
      setMessage(`Stream stop failed: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    refreshAll(false)
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
    <div className="space-y-3 text-sm panel-card p-4">
      <div className="flex items-center justify-between">
        <h3 className="panel-title">Advanced Operations</h3>
        <button
          type="button"
          disabled={busy}
          onClick={() => refreshAll(true)}
          className="px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 hover:bg-slate-200 transition-colors disabled:opacity-60"
        >
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 gap-2">
        <div className="p-3 rounded-xl border border-indigo-200 bg-indigo-50/70">
          <p className="font-semibold text-indigo-900">Realtime Stream (GPSFeed+)</p>
          <p className="text-xs text-indigo-700 mt-0.5">
            Status: {streamStatus?.running ? 'running' : 'stopped'}
            {' '}| Parsed: {streamStatus?.parsed_count ?? 0}
            {' '}| Rejected: {streamStatus?.rejected_count ?? 0}
          </p>
          <div className="mt-1 grid grid-cols-1 gap-1">
            <select value={streamProtocol} onChange={(e) => setStreamProtocol(e.target.value)} className="px-2.5 py-1.5 rounded-lg border border-indigo-200 bg-white">
              <option value="udp">UDP</option>
              <option value="tcp">TCP</option>
            </select>
            <input type="number" value={streamPort} onChange={(e) => setStreamPort(e.target.value)} className="px-2.5 py-1.5 rounded-lg border border-indigo-200 bg-white" />
            <select value={datasetProfile} onChange={(e) => setDatasetProfile(e.target.value)} className="px-2.5 py-1.5 rounded-lg border border-indigo-200 bg-white">
              <option value="strict">Strict Dataset</option>
              <option value="flexible">Flexible Dataset</option>
              <option value="vendor_x">Vendor-X Dataset</option>
            </select>
          </div>
          <div className="mt-2 flex gap-2">
            <button type="button" disabled={busy || !canOperate} onClick={onStartStream} className="px-3 py-1.5 rounded-lg bg-indigo-700 text-white hover:bg-indigo-800 disabled:opacity-60">Start Stream</button>
            <button type="button" disabled={busy || !canOperate} onClick={onStopStream} className="px-3 py-1.5 rounded-lg bg-slate-700 text-white hover:bg-slate-800 disabled:opacity-60">Stop Stream</button>
          </div>
        </div>

        <div className="p-3 rounded-xl border border-indigo-200 bg-indigo-50/70">
          <p className="font-semibold text-indigo-900">Notifications</p>
          <p className="text-xs text-indigo-700 mt-0.5">Channels: {channels.length}</p>
          <div className="mt-1 grid grid-cols-1 gap-1">
            <input value={channelName} onChange={(e) => setChannelName(e.target.value)} className="px-2.5 py-1.5 rounded-lg border border-indigo-200 bg-white" />
            <input value={channelType} onChange={(e) => setChannelType(e.target.value)} className="px-2.5 py-1.5 rounded-lg border border-indigo-200 bg-white" />
            <input value={channelRecipient} onChange={(e) => setChannelRecipient(e.target.value)} className="px-2.5 py-1.5 rounded-lg border border-indigo-200 bg-white" />
          </div>
          <button type="button" disabled={busy || !canOperate} onClick={onSaveChannel} className="mt-2 px-3 py-1.5 rounded-lg bg-indigo-700 text-white hover:bg-indigo-800 disabled:opacity-60">Save & Test</button>
        </div>

        <div className="p-3 rounded-xl border border-cyan-200 bg-cyan-50/70">
          <p className="font-semibold text-cyan-900">Rule Engine</p>
          <p className="text-xs text-cyan-700 mt-0.5">Rules: {rules.length}</p>
          <input value={ruleName} onChange={(e) => setRuleName(e.target.value)} className="mt-1 w-full px-2.5 py-1.5 rounded-lg border border-cyan-200 bg-white" />
          <button type="button" disabled={busy || !canOperate} onClick={onCreateRule} className="mt-2 px-3 py-1.5 rounded-lg bg-cyan-700 text-white hover:bg-cyan-800 disabled:opacity-60">Add Rule</button>
        </div>

        <div className="p-3 rounded-xl border border-emerald-200 bg-emerald-50/70">
          <p className="font-semibold text-emerald-900">Route Deviation</p>
          <p className="text-xs text-emerald-700 mt-0.5">Route plans: {routePlans.length}</p>
          <input value={routeName} onChange={(e) => setRouteName(e.target.value)} className="mt-1 w-full px-2.5 py-1.5 rounded-lg border border-emerald-200 bg-white" />
          <button type="button" disabled={busy || !canOperate} onClick={onCreateRoute} className="mt-2 px-3 py-1.5 rounded-lg bg-emerald-700 text-white hover:bg-emerald-800 disabled:opacity-60">Create Route</button>
        </div>

        <div className="p-3 rounded-xl border border-amber-200 bg-amber-50/70">
          <p className="font-semibold text-amber-900">Reporting & Intelligence</p>
          {reporting && <p className="text-xs text-amber-800 mt-1">24h alerts: {reporting.total_alerts} | resolved: {reporting.resolved_alerts} | avg speed: {reporting.avg_speed}</p>}
          {anomaly && <p className="text-xs text-amber-800 mt-1">Anomaly for {anomaly.device_id}: score {anomaly.anomaly_score} ({anomaly.reason})</p>}
        </div>

        {(isAdmin || canOperate) && (
          <div className="p-3 rounded-xl border border-rose-200 bg-rose-50/70">
            <p className="font-semibold text-rose-900">Teams & Users</p>
            <p className="text-xs text-rose-700 mt-0.5">Users: {users.length} | Teams: {teams.length}</p>
            {isAdmin && (
              <div className="mt-1 grid grid-cols-1 gap-1">
                <input value={newUsername} onChange={(e) => setNewUsername(e.target.value)} className="px-2.5 py-1.5 rounded-lg border border-rose-200 bg-white" />
                <input value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="px-2.5 py-1.5 rounded-lg border border-rose-200 bg-white" />
                <button type="button" disabled={busy} onClick={onCreateUser} className="px-3 py-1.5 rounded-lg bg-rose-700 text-white hover:bg-rose-800 disabled:opacity-60">Create User</button>
              </div>
            )}
            <div className="mt-1 grid grid-cols-1 gap-1">
              <input value={teamName} onChange={(e) => setTeamName(e.target.value)} className="px-2.5 py-1.5 rounded-lg border border-rose-200 bg-white" />
              <button type="button" disabled={busy || !canOperate} onClick={onCreateTeam} className="px-3 py-1.5 rounded-lg bg-rose-600 text-white hover:bg-rose-700 disabled:opacity-60">Create Team</button>
            </div>
          </div>
        )}

        {isAdmin && governance && (
          <div className="p-3 rounded-xl border border-slate-300 bg-slate-100/90">
            <p className="font-semibold text-slate-900">Data Governance</p>
            <p className="text-xs text-slate-700 mt-1">Mask IDs: {governance.mask_device_identifier ? 'yes' : 'no'} | Precision: {governance.mask_precision_decimals}</p>
            <button type="button" disabled={busy} onClick={onTightenGovernance} className="mt-2 px-3 py-1.5 rounded-lg bg-slate-800 text-white hover:bg-slate-900 disabled:opacity-60">Tighten Policy</button>
          </div>
        )}
      </div>

      {message && <p className="text-xs text-slate-600 rounded-lg bg-slate-100 px-2 py-1">{message}</p>}
    </div>
  )
}

export default AdvancedOpsPanel
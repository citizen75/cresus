import { useState, useEffect } from 'react'
import { api } from '../services/api'

interface Alert {
  name: string
  source: string
  source_value?: string
  formula: string
  notify: string
  enabled: boolean
  created_at: string
  updated_at: string
  last_run?: string
  description?: string
  tags?: string[]
}

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedAlert, setSelectedAlert] = useState<string | null>(null)
  const [editingAlert, setEditingAlert] = useState<Alert | null>(null)
  const [runningAlert, setRunningAlert] = useState<string | null>(null)
  const [runResults, setRunResults] = useState<any>(null)
  const [activeTab, setActiveTab] = useState<'alerts' | 'logs'>('alerts')
  const [selectedAlertForLogs, setSelectedAlertForLogs] = useState<string | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [formData, setFormData] = useState<Partial<Alert>>({})
  const [resultViewMode, setResultViewMode] = useState<'table' | 'charts'>('table')
  const [resultSearchQuery, setResultSearchQuery] = useState('')
  const [resultSortColumn, setResultSortColumn] = useState<string | null>('ticker')
  const [resultSortDirection, setResultSortDirection] = useState<'asc' | 'desc'>('asc')
  const [newAlertData, setNewAlertData] = useState({
    name: '',
    source: 'universe',
    source_value: 'cac40',
    formula: '',
    notify: 'conversation',
    description: '',
  })

  // Fetch alerts on mount
  useEffect(() => {
    fetchAlerts()
  }, [])

  // Auto-refresh alerts periodically (skip while alert is running)
  useEffect(() => {
    if (runningAlert) return
    const interval = setInterval(fetchAlerts, 5000)
    return () => clearInterval(interval)
  }, [runningAlert])

  // Refresh alerts list when results arrive
  useEffect(() => {
    if (runResults && !runningAlert) {
      fetchAlerts()
    }
  }, [runResults])

  const fetchAlerts = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.listAlerts()
      setAlerts(response.alerts || [])
    } catch (err) {
      const errorMsg = `Failed to load alerts: ${err instanceof Error ? err.message : 'Unknown error'}`
      console.error(errorMsg, err)
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const loadAlertLogs = async (alertName: string) => {
    try {
      setLogsLoading(true)
      const response = await api.getAlertLogs(alertName, 200)
      setLogs(response.logs || [])
      setError(null)
    } catch (err) {
      setError('Failed to load alert logs')
      console.error(err)
    } finally {
      setLogsLoading(false)
    }
  }

  const runAlert = async (name: string) => {
    setRunningAlert(name)
    try {
      const response = await api.runAlert(name)
      setRunResults(response)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run alert')
    } finally {
      setRunningAlert(null)
    }
  }

  const createAlert = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.createAlert(newAlertData)
      setNewAlertData({
        name: '',
        source: 'universe',
        source_value: 'cac40',
        formula: '',
        notify: 'conversation',
        description: '',
      })
      setShowCreateModal(false)
      await fetchAlerts()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create alert')
    }
  }

  const startEdit = (alert: Alert) => {
    setEditingAlert(alert)
    setFormData({
      formula: alert.formula,
      description: alert.description,
      notify: alert.notify,
      enabled: alert.enabled,
    })
    setEditMode(true)
  }

  const cancelEdit = () => {
    setEditMode(false)
    setEditingAlert(null)
    setFormData({})
  }

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.currentTarget as HTMLInputElement
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? (e.currentTarget as HTMLInputElement).checked : value,
    })
  }

  const saveAlert = async (name: string) => {
    try {
      await api.updateAlert(name, formData)
      cancelEdit()
      await fetchAlerts()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update alert')
    }
  }

  const deleteAlert = async (name: string) => {
    if (!confirm(`Delete alert "${name}"?`)) return
    try {
      await api.deleteAlert(name)
      if (selectedAlert === name) {
        setSelectedAlert(null)
        setEditingAlert(null)
      }
      await fetchAlerts()
    } catch (err) {
      setError('Failed to delete alert')
    }
  }

  const formatMessageDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return 'Just now'
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    if (days < 7) return `${days}d ago`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const getResultColumns = () => {
    if (!runResults?.matches || runResults.matches.length === 0) return []
    const firstMatch = runResults.matches[0]
    return Object.keys(firstMatch).filter((key) => key !== 'Index')
  }

  const filteredResults = runResults?.matches
    ? runResults.matches.filter((match: any) => {
        if (!resultSearchQuery.trim()) return true
        const query = resultSearchQuery.toLowerCase()
        return Object.values(match).some((val) =>
          String(val).toLowerCase().includes(query)
        )
      })
    : []

  const sortedResults = [...filteredResults].sort((a: any, b: any) => {
    if (!resultSortColumn) return 0
    const aVal = a[resultSortColumn]
    const bVal = b[resultSortColumn]

    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return resultSortDirection === 'asc' ? aVal - bVal : bVal - aVal
    }

    const aStr = String(aVal).toLowerCase()
    const bStr = String(bVal).toLowerCase()
    if (resultSortDirection === 'asc') {
      return aStr.localeCompare(bStr)
    } else {
      return bStr.localeCompare(aStr)
    }
  })

  const currentAlert = selectedAlert ? alerts.find((a) => a.name === selectedAlert) : null

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-start justify-between px-4 py-3 border-b border-slate-800">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Alerts</h1>
          <p className="text-slate-400 text-sm">Create and manage screener formula alerts</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchAlerts}
            disabled={loading}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-medium transition disabled:opacity-50"
            title="Refresh alerts list"
          >
            ⟳
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition"
          >
            + Create Alert
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-slate-800 px-4">
        <button
          onClick={() => setActiveTab('alerts')}
          className={`px-4 py-2 font-medium transition ${
            activeTab === 'alerts'
              ? 'text-white border-b-2 border-purple-500'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          Alerts
        </button>
        <button
          onClick={() => setActiveTab('logs')}
          className={`px-4 py-2 font-medium transition ${
            activeTab === 'logs'
              ? 'text-white border-b-2 border-purple-500'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          Logs
        </button>
      </div>

      {/* Alert Editor (Like Screener Detail) */}
      {activeTab === 'alerts' && (
        <div className="flex-1 flex flex-col gap-4 px-4 min-h-0 overflow-hidden">
          {error && (
            <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 text-red-300 flex items-start justify-between gap-4">
              <div>
                <p className="font-bold mb-1">Error</p>
                <p className="text-sm">{error}</p>
              </div>
              <button onClick={() => setError(null)} className="text-red-300 hover:text-red-100">
                ✕
              </button>
            </div>
          )}

          {!currentAlert ? (
            // Alert List
            <div className="flex-1 overflow-auto">
              {loading ? (
                <div className="bg-slate-900/50 rounded-lg p-12 border border-slate-800 text-center">
                  <p className="text-slate-400">Loading alerts...</p>
                </div>
              ) : alerts.length === 0 ? (
                <div className="bg-slate-900/50 rounded-lg p-8 border border-slate-800 text-center">
                  <p className="text-slate-400 text-lg mb-2">No alerts configured</p>
                  <p className="text-slate-500 text-sm">Create your first alert to monitor market conditions</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {alerts.map((alert) => (
                    <div
                      key={alert.name}
                      onClick={() => setSelectedAlert(alert.name)}
                      className="bg-slate-900 border border-slate-800 rounded-lg p-4 cursor-pointer hover:border-purple-500 transition"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-semibold text-white truncate">{alert.name}</h3>
                        <span
                          className={`text-xs px-2 py-1 rounded ${
                            alert.enabled
                              ? 'bg-green-900/30 text-green-400'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {alert.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mb-3 font-mono break-words">
                        {alert.formula}
                      </p>
                      <p className="text-xs text-slate-500">Source: {alert.source}</p>
                      {alert.last_run && (
                        <p className="text-xs text-slate-500 mt-1">Last run: {formatMessageDate(alert.last_run)}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            // Alert Editor (Grid Layout - Form Left, Last Result Right, Results Bottom)
            <>
              <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-0 overflow-hidden">
                {/* Left: Configuration Form (3 columns) */}
                <div className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-lg p-6 overflow-y-auto">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-white">Configuration</h2>
                    <button
                      onClick={() => setSelectedAlert(null)}
                      className="text-slate-400 hover:text-slate-200"
                    >
                      ✕
                    </button>
                  </div>

                  {editMode ? (
                    <form className="space-y-4">
                      <div>
                        <label className="block text-sm text-slate-400 mb-2">Formula</label>
                        <textarea
                          name="formula"
                          value={formData.formula || ''}
                          onChange={handleFormChange}
                          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500 font-mono"
                          rows={3}
                        />
                      </div>

                      <div>
                        <label className="block text-sm text-slate-400 mb-2">Notify</label>
                        <select
                          name="notify"
                          value={formData.notify || currentAlert?.notify || ''}
                          onChange={handleFormChange}
                          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                        >
                          <option value="conversation">Conversation (per portfolio)</option>
                          <option value="global">Global (all matches)</option>
                          <option value="email">Email</option>
                          <option value="webhook">Webhook</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm text-slate-400 mb-2">Description</label>
                        <input
                          type="text"
                          name="description"
                          value={formData.description || ''}
                          onChange={handleFormChange}
                          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                        />
                      </div>

                      <label className="flex items-center gap-2 text-sm text-slate-400">
                        <input
                          type="checkbox"
                          name="enabled"
                          checked={formData.enabled !== undefined ? formData.enabled : currentAlert?.enabled}
                          onChange={handleFormChange}
                          className="rounded"
                        />
                        Enabled
                      </label>

                      <div className="flex gap-3 pt-4 border-t border-slate-700">
                        <button
                          type="button"
                          onClick={() => saveAlert(currentAlert?.name!)}
                          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium transition"
                        >
                          Save
                        </button>
                        <button
                          type="button"
                          onClick={cancelEdit}
                          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium transition"
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  ) : (
                    <div className="space-y-4">
                      <div>
                        <div className="text-sm text-slate-500">Source</div>
                        <div className="text-white font-medium mt-1">{currentAlert?.source}</div>
                      </div>

                      <div>
                        <div className="text-sm text-slate-500">Formula</div>
                        <div className="text-white font-mono text-xs mt-1 break-words bg-slate-800 p-3 rounded">
                          {currentAlert?.formula}
                        </div>
                      </div>

                      <div>
                        <div className="text-sm text-slate-500">Notify</div>
                        <div className="text-white font-medium mt-1">{currentAlert?.notify}</div>
                      </div>

                      {currentAlert?.description && (
                        <div>
                          <div className="text-sm text-slate-500">Description</div>
                          <div className="text-white mt-1">{currentAlert?.description}</div>
                        </div>
                      )}

                      <div>
                        <div className="text-sm text-slate-500">Status</div>
                        <div className={`text-white font-medium mt-1 ${currentAlert?.enabled ? 'text-green-400' : 'text-red-400'}`}>
                          {currentAlert?.enabled ? '✓ Enabled' : '✗ Disabled'}
                        </div>
                      </div>

                      <div className="flex gap-3 pt-4 border-t border-slate-700">
                        <button
                          type="button"
                          onClick={() => startEdit(currentAlert!)}
                          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium transition"
                        >
                          ✏️ Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => runAlert(currentAlert?.name!)}
                          disabled={runningAlert === currentAlert?.name}
                          className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded font-medium transition"
                        >
                          {runningAlert === currentAlert?.name ? '⏳ Running...' : '▶ Run Now'}
                        </button>
                        <button
                          type="button"
                          onClick={() => deleteAlert(currentAlert?.name!)}
                          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded font-medium transition"
                        >
                          🗑 Delete
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Right: Last Result (1 column) */}
                <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 overflow-y-auto">
                  <h2 className="text-lg font-semibold text-white mb-4">Last Result</h2>

                  {runResults && runResults.alert_name === currentAlert?.name ? (
                    <div className="space-y-3 text-sm">
                      <div>
                        <div className="text-slate-400">Status</div>
                        <div className={`font-bold mt-1 ${runResults.matched ? 'text-green-400' : 'text-slate-400'}`}>
                          {runResults.matched ? '✓ Matched' : '✗ No Match'}
                        </div>
                      </div>

                      <div>
                        <div className="text-slate-400">Matches</div>
                        <div className="text-white font-medium mt-1">{runResults.matches?.length || 0}</div>
                      </div>

                      <div>
                        <div className="text-slate-400">Tickers Checked</div>
                        <div className="text-white font-medium mt-1">{runResults.tickers_checked}</div>
                      </div>

                      {runResults.error && (
                        <div className="bg-red-900/30 border border-red-700 rounded p-2 text-red-300 text-xs">
                          {runResults.error}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-6 text-slate-500">
                      <p>No recent run</p>
                      <p className="text-xs mt-2">Run the alert to see results</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Results Table (Bottom) */}
              {currentAlert && runResults && runResults.matches && runResults.matches.length > 0 && (
                <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex flex-col flex-1 min-h-0">
                  {/* Results Header */}
                  <div className="bg-slate-800 px-6 py-4 border-b border-slate-700 flex items-center justify-between flex-shrink-0">
                    <h3 className="font-semibold text-white">
                      Results ({filteredResults.length} of {runResults.matches.length} matches)
                    </h3>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setResultViewMode('table')}
                        className={`px-3 py-1 rounded text-sm font-medium transition ${
                          resultViewMode === 'table'
                            ? 'bg-purple-600 text-white'
                            : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                        }`}
                      >
                        📊 Table
                      </button>
                      <button
                        onClick={() => setResultViewMode('charts')}
                        className={`px-3 py-1 rounded text-sm font-medium transition ${
                          resultViewMode === 'charts'
                            ? 'bg-purple-600 text-white'
                            : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                        }`}
                      >
                        📈 Charts
                      </button>
                    </div>
                  </div>

                  {/* Search Bar */}
                  <div className="px-6 py-3 border-b border-slate-700 flex-shrink-0">
                    <input
                      type="text"
                      placeholder="Search results..."
                      value={resultSearchQuery}
                      onChange={(e) => setResultSearchQuery(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm placeholder-slate-500 focus:outline-none focus:border-purple-500"
                    />
                  </div>

                  {/* Table View */}
                  {resultViewMode === 'table' && (
                    <div className="flex-1 overflow-auto">
                      <table className="w-full text-xs">
                        <thead className="sticky top-0 bg-slate-800 border-b border-slate-700">
                          <tr>
                            {getResultColumns().map((col) => (
                              <th
                                key={col}
                                onClick={() => {
                                  if (resultSortColumn === col) {
                                    setResultSortDirection(
                                      resultSortDirection === 'asc' ? 'desc' : 'asc'
                                    )
                                  } else {
                                    setResultSortColumn(col)
                                    setResultSortDirection('asc')
                                  }
                                }}
                                className="px-4 py-3 text-left text-slate-400 font-medium cursor-pointer hover:text-slate-300 transition whitespace-nowrap"
                              >
                                {col}
                                {resultSortColumn === col && (
                                  <span className="ml-1">
                                    {resultSortDirection === 'asc' ? '↑' : '↓'}
                                  </span>
                                )}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                          {sortedResults.map((match: any, idx: number) => (
                            <tr key={idx} className="hover:bg-slate-800/50 transition">
                              {getResultColumns().map((col) => (
                                <td
                                  key={`${idx}-${col}`}
                                  className="px-4 py-3 text-slate-300 whitespace-nowrap"
                                >
                                  {typeof match[col] === 'number'
                                    ? match[col].toFixed(3)
                                    : match[col]}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Charts View */}
                  {resultViewMode === 'charts' && (
                    <div className="flex-1 overflow-auto p-6 flex items-center justify-center">
                      <div className="text-center text-slate-500">
                        <p className="text-lg mb-2">📈 Charts View</p>
                        <p className="text-sm">Chart visualization coming soon</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Logs Tab */}
      {activeTab === 'logs' && (
        <div className="flex-1 flex flex-col gap-4 px-4 min-h-0 overflow-hidden">
          <div className="flex gap-2">
            <select
              value={selectedAlertForLogs || ''}
              onChange={(e) => {
                const alertName = e.target.value
                setSelectedAlertForLogs(alertName)
                if (alertName) loadAlertLogs(alertName)
              }}
              className="px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded-lg text-sm focus:outline-none focus:border-purple-500"
            >
              <option value="">Select an alert to view logs...</option>
              {alerts.map((alert) => (
                <option key={alert.name} value={alert.name}>
                  {alert.name}
                </option>
              ))}
            </select>
            {selectedAlertForLogs && (
              <button
                onClick={() => selectedAlertForLogs && loadAlertLogs(selectedAlertForLogs)}
                className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm transition"
              >
                🔄 Refresh
              </button>
            )}
          </div>

          {selectedAlertForLogs ? (
            <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex flex-col flex-1 min-h-0">
              <div className="bg-slate-800 px-4 py-3 border-b border-slate-700">
                <h3 className="font-semibold text-white">Logs for: {selectedAlertForLogs}</h3>
              </div>
              <div className="p-4 max-h-full overflow-y-auto flex-1">
                {logsLoading ? (
                  <div className="text-center text-slate-500">Loading logs...</div>
                ) : logs.length === 0 ? (
                  <div className="text-center text-slate-500 text-sm">No logs yet</div>
                ) : (
                  <div className="font-mono text-xs space-y-0">
                    {logs.map((line, idx) => (
                      <div
                        key={idx}
                        className={`py-1 px-2 ${
                          line.includes('ERROR')
                            ? 'text-red-400 bg-red-900/10'
                            : line.includes('WARNING')
                              ? 'text-yellow-400 bg-yellow-900/10'
                              : line.includes('INFO')
                                ? 'text-blue-400'
                                : 'text-slate-400'
                        }`}
                      >
                        {line}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-center py-12 bg-slate-900 border border-slate-800 rounded-lg flex-1 flex items-center justify-center">
              <div className="text-slate-500">Select an alert to view its logs</div>
            </div>
          )}
        </div>
      )}

      {/* Create Alert Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-lg w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-slate-900 border-b border-slate-800 p-6 flex items-center justify-between">
              <h2 className="text-2xl font-bold text-white">Create New Alert</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white transition"
              >
                ✕
              </button>
            </div>

            <form onSubmit={createAlert} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Alert Name</label>
                <input
                  type="text"
                  value={newAlertData.name}
                  onChange={(e) => setNewAlertData({ ...newAlertData, name: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded focus:outline-none focus:border-purple-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Source</label>
                <select
                  value={newAlertData.source}
                  onChange={(e) => setNewAlertData({ ...newAlertData, source: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded focus:outline-none focus:border-purple-500"
                >
                  <option value="universe">Universe</option>
                  <option value="ticker">Ticker</option>
                  <option value="tickers">Tickers</option>
                  <option value="portfolio">Portfolio</option>
                  <option value="all_portfolios">All Portfolios</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Source Value</label>
                <input
                  type="text"
                  value={newAlertData.source_value}
                  onChange={(e) => setNewAlertData({ ...newAlertData, source_value: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded focus:outline-none focus:border-purple-500"
                  placeholder="e.g., cac40, AAPL"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Formula</label>
                <textarea
                  value={newAlertData.formula}
                  onChange={(e) => setNewAlertData({ ...newAlertData, formula: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded focus:outline-none focus:border-purple-500 font-mono text-sm"
                  rows={3}
                  placeholder="e.g., sha_10_green[-1]==1 && sha_10_up[0]==1"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Notify</label>
                <select
                  value={newAlertData.notify}
                  onChange={(e) => setNewAlertData({ ...newAlertData, notify: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded focus:outline-none focus:border-purple-500"
                >
                  <option value="conversation">Conversation (per portfolio)</option>
                  <option value="global">Global (all matches)</option>
                  <option value="email">Email</option>
                  <option value="webhook">Webhook</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Description (optional)</label>
                <input
                  type="text"
                  value={newAlertData.description}
                  onChange={(e) => setNewAlertData({ ...newAlertData, description: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="flex gap-3 pt-4 border-t border-slate-700">
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium transition"
                >
                  Create Alert
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium transition"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

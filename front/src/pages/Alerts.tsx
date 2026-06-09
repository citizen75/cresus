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
  const [editingAlert, setEditingAlert] = useState<Alert | null>(null)
  const [runningAlert, setRunningAlert] = useState<string | null>(null)
  const [runResults, setRunResults] = useState<any>(null)
  const [showRunResults, setShowRunResults] = useState(false)

  const [formData, setFormData] = useState({
    name: '',
    source: 'ticker',
    source_value: '',
    formula: '',
    notify: 'conversation',
    description: '',
  })

  // Fetch alerts
  useEffect(() => {
    fetchAlerts()
  }, [])

  const fetchAlerts = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.listAlerts()
      setAlerts(response.alerts || [])
    } catch (err) {
      setError(`Failed to load alerts: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateAlert = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setError(null)
      await api.createAlert(formData)
      setShowCreateModal(false)
      setFormData({
        name: '',
        source: 'ticker',
        source_value: '',
        formula: '',
        notify: 'conversation',
        description: '',
      })
      await fetchAlerts()
    } catch (err) {
      setError(`Failed to create alert: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const handleUpdateAlert = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingAlert) return

    try {
      setError(null)
      await api.updateAlert(editingAlert.name, {
        formula: formData.formula,
        notify: formData.notify,
        description: formData.description,
        enabled: editingAlert.enabled,
      })
      setEditingAlert(null)
      setFormData({
        name: '',
        source: 'ticker',
        source_value: '',
        formula: '',
        notify: 'conversation',
        description: '',
      })
      await fetchAlerts()
    } catch (err) {
      setError(`Failed to update alert: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const handleDeleteAlert = async (name: string) => {
    if (!confirm(`Delete alert "${name}"?`)) return

    try {
      setError(null)
      await api.deleteAlert(name)
      await fetchAlerts()
    } catch (err) {
      setError(`Failed to delete alert: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const handleToggleEnabled = async (alert: Alert) => {
    try {
      setError(null)
      await api.updateAlert(alert.name, {
        enabled: !alert.enabled,
      })
      await fetchAlerts()
    } catch (err) {
      setError(`Failed to update alert: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const handleRunAlert = async (name: string) => {
    try {
      setError(null)
      setRunningAlert(name)
      const response = await api.runAlert(name)
      setRunResults(response)
      setShowRunResults(true)
      await fetchAlerts() // Refresh to get updated last_run timestamp
    } catch (err) {
      setError(`Failed to run alert: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setRunningAlert(null)
    }
  }

  const openEditModal = (alert: Alert) => {
    setEditingAlert(alert)
    setFormData({
      name: alert.name,
      source: alert.source,
      source_value: alert.source_value || '',
      formula: alert.formula,
      notify: alert.notify,
      description: alert.description || '',
    })
    setShowCreateModal(true)
  }

  const closeModals = () => {
    setShowCreateModal(false)
    setEditingAlert(null)
    setFormData({
      name: '',
      source: 'ticker',
      source_value: '',
      formula: '',
      notify: 'conversation',
      description: '',
    })
  }

  const sourceOptions = [
    { value: 'ticker', label: 'Single Ticker' },
    { value: 'tickers', label: 'Multiple Tickers (comma-separated)' },
    { value: 'universe', label: 'Universe' },
    { value: 'portfolio', label: 'Portfolio' },
    { value: 'all_portfolios', label: 'All Real Portfolios' },
  ]

  const notifyOptions = [
    { value: 'conversation', label: 'Conversation' },
    { value: 'email', label: 'Email' },
    { value: 'webhook', label: 'Webhook' },
  ]

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">Alerts</h1>
          <p className="text-slate-400">Create and manage screener formula alerts</p>
        </div>
        <button
          onClick={() => {
            setEditingAlert(null)
            setShowCreateModal(true)
          }}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition"
        >
          + Create Alert
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-900/30 border border-red-800 rounded-lg p-4 text-red-400">
          {error}
        </div>
      )}

      {/* Alerts List */}
      {loading ? (
        <div className="bg-slate-900/50 rounded-lg p-12 border border-slate-800 text-center">
          <p className="text-slate-400">Loading alerts...</p>
        </div>
      ) : alerts.length === 0 ? (
        <div className="bg-slate-900/50 rounded-lg p-12 border border-slate-800 text-center">
          <p className="text-slate-400 text-lg mb-2">No alerts configured</p>
          <p className="text-slate-500 text-sm mb-4">Create your first alert to monitor screener formulas</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition"
          >
            Create Alert
          </button>
        </div>
      ) : (
        <div className="space-y-1.5">
          {alerts.map((alert) => (
            <div
              key={alert.name}
              className="bg-slate-900/30 border border-slate-800 rounded p-2.5 hover:border-slate-700 hover:bg-slate-900/50 transition"
            >
              <div className="flex items-center justify-between gap-3">
                {/* Alert Info - Compact */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-sm font-bold text-white">{alert.name}</h3>
                    <span className={`inline-flex px-1.5 py-0.5 rounded text-xs font-medium ${
                      alert.enabled
                        ? 'bg-green-900/30 border border-green-800 text-green-400'
                        : 'bg-slate-800 text-slate-400'
                    }`}>
                      {alert.enabled ? '✓' : '○'}
                    </span>
                    <span className="text-xs text-slate-500">
                      {alert.source}
                      {alert.source_value && ` (${alert.source_value})`}
                    </span>
                    <span className="text-xs text-slate-400">•</span>
                    <code className="text-xs text-slate-400 overflow-hidden text-ellipsis max-w-xs">
                      {alert.formula.substring(0, 50)}{alert.formula.length > 50 ? '...' : ''}
                    </code>
                  </div>
                  <div className="text-xs text-slate-500 mt-1 flex gap-3">
                    <span>{alert.notify}</span>
                    <span>Last: {formatDate(alert.last_run)}</span>
                    {alert.description && <span className="text-slate-600 italic truncate">{alert.description}</span>}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <button
                    onClick={() => handleRunAlert(alert.name)}
                    disabled={runningAlert === alert.name}
                    className="px-2 py-1 text-xs bg-blue-900/30 hover:bg-blue-900/50 border border-blue-800 text-blue-400 rounded transition disabled:opacity-50"
                    title="Run alert"
                  >
                    {runningAlert === alert.name ? '⟳' : '▶'}
                  </button>
                  <button
                    onClick={() => handleToggleEnabled(alert)}
                    className={`px-2 py-1 text-xs rounded transition border ${
                      alert.enabled
                        ? 'bg-green-900/30 hover:bg-green-900/50 border-green-800 text-green-400'
                        : 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-400'
                    }`}
                    title={alert.enabled ? 'Disable' : 'Enable'}
                  >
                    {alert.enabled ? '✓' : '○'}
                  </button>
                  <button
                    onClick={() => openEditModal(alert)}
                    className="px-2 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition"
                    title="Edit"
                  >
                    ✎
                  </button>
                  <button
                    onClick={() => handleDeleteAlert(alert.name)}
                    className="px-2 py-1 text-xs bg-slate-800 hover:bg-red-900/20 text-slate-300 hover:text-red-400 rounded transition"
                    title="Delete"
                  >
                    ✕
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-slate-900 border-b border-slate-800 p-6 flex items-center justify-between">
              <h2 className="text-2xl font-bold text-white">
                {editingAlert ? 'Edit Alert' : 'Create New Alert'}
              </h2>
              <button
                onClick={closeModals}
                className="text-slate-400 hover:text-white transition"
              >
                ✕
              </button>
            </div>

            <form
              onSubmit={editingAlert ? handleUpdateAlert : handleCreateAlert}
              className="p-6 space-y-4"
            >
              {/* Name */}
              {!editingAlert && (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Alert Name *
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., rsi_oversold"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-purple-600"
                    required
                  />
                </div>
              )}

              {/* Source (read-only when editing, editable when creating) */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Source *
                </label>
                {editingAlert ? (
                  <div className="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-3 py-2 text-slate-300 text-sm">
                    {formData.source}
                    {formData.source_value && ` (${formData.source_value})`}
                  </div>
                ) : (
                  <select
                    value={formData.source}
                    onChange={(e) => setFormData({ ...formData, source: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-600"
                  >
                    {sourceOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Source Value */}
              {!editingAlert && formData.source !== 'all_portfolios' && (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    {formData.source === 'ticker' ? 'Ticker' : 'Value'} {formData.source !== 'ticker' && formData.source !== 'tickers' && '*'}
                  </label>
                  <input
                    type="text"
                    value={formData.source_value}
                    onChange={(e) => setFormData({ ...formData, source_value: e.target.value })}
                    placeholder={
                      formData.source === 'tickers'
                        ? 'AAPL,MSFT,GOOGL'
                        : formData.source === 'universe'
                        ? 'cac40'
                        : 'Portfolio name'
                    }
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-purple-600"
                    required={formData.source !== 'ticker' && formData.source !== 'tickers'}
                  />
                </div>
              )}

              {/* Formula */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  DSL Formula *
                </label>
                <textarea
                  value={formData.formula}
                  onChange={(e) => setFormData({ ...formData, formula: e.target.value })}
                  placeholder="e.g., rsi_14[0] > 50 && ema_20[0] > close[0]"
                  rows={4}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-purple-600 font-mono text-sm"
                  required
                />
                <p className="text-xs text-slate-500 mt-1">
                  Use DSL syntax: rsi_14[0], ema_20[-1], close[0], volume[0], etc.
                </p>
              </div>

              {/* Notify Target */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Notify Target
                </label>
                <select
                  value={formData.notify}
                  onChange={(e) => setFormData({ ...formData, notify: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-600"
                >
                  {notifyOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Optional description"
                  rows={2}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-purple-600"
                />
              </div>

              {/* Actions */}
              <div className="flex items-center gap-3 pt-4">
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition"
                >
                  {editingAlert ? 'Update Alert' : 'Create Alert'}
                </button>
                <button
                  type="button"
                  onClick={closeModals}
                  className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-medium transition"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Run Results Modal */}
      {showRunResults && runResults && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-slate-900 border-b border-slate-800 p-6 flex items-center justify-between">
              <h2 className="text-2xl font-bold text-white">
                Alert Results: {runResults.alert_name}
              </h2>
              <button
                onClick={() => setShowRunResults(false)}
                className="text-slate-400 hover:text-white transition"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-4">
              {runResults.error ? (
                <div className="bg-red-900/30 border border-red-800 rounded-lg p-4 text-red-400">
                  <p className="font-medium mb-1">Error</p>
                  <p className="text-sm">{runResults.error}</p>
                </div>
              ) : (
                <>
                  {/* Summary */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                      <p className="text-slate-400 text-sm mb-1">Status</p>
                      <p className={`text-lg font-bold ${runResults.matched ? 'text-green-400' : 'text-slate-400'}`}>
                        {runResults.matched ? '✓ Matched' : '○ No matches'}
                      </p>
                    </div>
                    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                      <p className="text-slate-400 text-sm mb-1">Tickers Checked</p>
                      <p className="text-lg font-bold text-white">{runResults.tickers_checked}</p>
                    </div>
                    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                      <p className="text-slate-400 text-sm mb-1">Matches Found</p>
                      <p className="text-lg font-bold text-white">{runResults.matches?.length || 0}</p>
                    </div>
                  </div>

                  {/* Matches Table */}
                  {runResults.matches && runResults.matches.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-slate-300 mb-2">Top Matches (max 50)</p>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead className="bg-slate-800/50 border-b border-slate-700">
                            <tr>
                              <th className="px-3 py-2 text-left text-slate-400">Date</th>
                              <th className="px-3 py-2 text-left text-slate-400">Ticker</th>
                              <th className="px-3 py-2 text-right text-slate-400">Close</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800">
                            {runResults.matches.slice(0, 50).map((match: any, idx: number) => (
                              <tr key={idx} className="hover:bg-slate-800/30">
                                <td className="px-3 py-2 text-slate-300">
                                  {match.timestamp || match.date || '—'}
                                </td>
                                <td className="px-3 py-2 text-white font-medium">{match.ticker}</td>
                                <td className="px-3 py-2 text-right text-slate-300">
                                  {typeof match.close === 'number' ? match.close.toFixed(2) : '—'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      {runResults.matches.length > 50 && (
                        <p className="text-xs text-slate-500 mt-2">
                          Showing 50 of {runResults.matches.length} matches
                        </p>
                      )}
                    </div>
                  )}

                  <p className="text-xs text-slate-500">
                    Evaluated at: {new Date(runResults.evaluated_at).toLocaleString()}
                  </p>
                </>
              )}

              <button
                onClick={() => setShowRunResults(false)}
                className="w-full px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-medium transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

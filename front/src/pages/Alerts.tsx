import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { api } from '../services/api'
import CardChart from '@/components/CardChart'
import TradingChartWidget from '@/components/TradingChartWidget'
import ResultsWidget from '@/components/ResultsWidget'

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
  const { name: paramName, resultId: paramResultId, view: viewParam } = useParams<{ name?: string; resultId?: string; view?: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const isEditMode = location.pathname.includes('/edit')

  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingAlert, setEditingAlert] = useState<Alert | null>(null)
  const [runningAlert, setRunningAlert] = useState<string | null>(null)
  const [runResults, setRunResults] = useState<any>(null)
  const [activeTab, setActiveTab] = useState<'alerts' | 'logs'>('alerts')
  const [selectedAlertForLogs, setSelectedAlertForLogs] = useState<string | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [formData, setFormData] = useState<Partial<Alert>>({})
  const [resultViewMode, setResultViewMode] = useState<'table' | 'charts'>(viewParam === 'charts' ? 'charts' : 'table')
  const [resultSearchQuery, setResultSearchQuery] = useState('')
  const [resultSortColumn, setResultSortColumn] = useState<string | null>('ticker')
  const [resultSortDirection, setResultSortDirection] = useState<'asc' | 'desc'>('asc')
  const [chartTimeframe, setChartTimeframe] = useState<'1W' | '1M' | '3M' | 'YTD' | 'ALL'>('1M')
  const [historicalData, setHistoricalData] = useState<{ [ticker: string]: any[] }>({})
  const [loadingCharts, setLoadingCharts] = useState(false)
  const [selectedTickerForChart, setSelectedTickerForChart] = useState<string | null>(null)
  const [savedResults, setSavedResults] = useState<any[]>([])
  const [loadingSavedResults, setLoadingSavedResults] = useState(false)
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

  // Don't auto-refresh - only refresh when explicitly needed
  // useEffect(() => {
  //   if (runningAlert) return
  //   const interval = setInterval(fetchAlerts, 5000)
  //   return () => clearInterval(interval)
  // }, [runningAlert])

  // Refresh alerts list when results arrive
  useEffect(() => {
    if (runResults && !runningAlert) {
      fetchAlerts()
    }
  }, [runResults])

  // Load saved results when alert name changes from URL
  useEffect(() => {
    if (paramName) {
      loadSavedResults(paramName)
    }
  }, [paramName])

  // Set edit mode based on URL
  useEffect(() => {
    if (isEditMode && paramName && alerts.length > 0) {
      const alert = alerts.find(a => a.name === paramName)
      if (alert) {
        setEditingAlert(alert)
        setFormData({
          formula: alert.formula,
          description: alert.description,
          notify: alert.notify,
          enabled: alert.enabled,
          name: alert.name,
          source: alert.source,
          source_value: alert.source_value,
        })
        setEditMode(true)
      }
    } else if (!isEditMode) {
      setEditMode(false)
      setEditingAlert(null)
      setFormData({})
    }
  }, [isEditMode, paramName, alerts])

  // Auto-load logs for currently viewed alert
  useEffect(() => {
    if (paramName && !paramResultId && !isEditMode) {
      // Auto-select and load logs for the current alert
      setSelectedAlertForLogs(paramName)
      loadAlertLogs(paramName)
    }
  }, [paramName, paramResultId, isEditMode])

  const fetchAlerts = async () => {
    try {
      setLoading(true)
      setError(null)
      console.log('Fetching alerts from API...')
      const response = await api.listAlerts()
      console.log('Alerts response:', response)
      if (Array.isArray(response)) {
        setAlerts(response)
      } else if (response && response.alerts && Array.isArray(response.alerts)) {
        setAlerts(response.alerts)
      } else {
        console.warn('Unexpected response format:', response)
        setAlerts([])
      }
    } catch (err) {
      let errorMsg = 'Failed to load alerts: '
      if (err instanceof Error) {
        errorMsg += err.message
      } else if (err && typeof err === 'object') {
        errorMsg += JSON.stringify(err)
      } else {
        errorMsg += 'Unknown error'
      }
      console.error('Alert fetch error:', err)
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
      name: alert.name,
      source: alert.source,
      source_value: alert.source_value,
    })
    navigate(`/alerts/${encodeURIComponent(alert.name)}/edit`)
  }

  const cancelEdit = () => {
    setEditMode(false)
    setEditingAlert(null)
    setFormData({})
    if (paramName) {
      navigate(`/alerts/${encodeURIComponent(paramName)}`)
    } else {
      navigate('/alerts')
    }
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
      // Handle name change (rename)
      if (formData.name && formData.name !== name) {
        // Delete old alert and create new one with renamed name
        const newName = formData.name
        const updateData = { ...formData }
        delete updateData.name // Remove name from update data

        // Create new alert with new name
        await api.createAlert({
          name: newName,
          source: formData.source || currentAlert?.source,
          source_value: currentAlert?.source_value,
          formula: formData.formula || currentAlert?.formula,
          notify: formData.notify || currentAlert?.notify,
          description: formData.description || currentAlert?.description,
          tags: currentAlert?.tags
        })

        // Delete old alert
        await api.deleteAlert(name)

        // Navigate to new alert
        navigate(`/alerts/${encodeURIComponent(newName)}`)
      } else {
        // Regular update without rename
        await api.updateAlert(name, {
          formula: formData.formula,
          description: formData.description,
          notify: formData.notify,
          enabled: formData.enabled,
          source: formData.source,
          source_value: formData.source_value,
        })
      }

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
      if (paramName === name) {
        navigate('/alerts')
        setEditingAlert(null)
      }
      await fetchAlerts()
    } catch (err) {
      setError('Failed to delete alert')
    }
  }

  const duplicateAlert = async (name: string) => {
    try {
      const alert = alerts.find(a => a.name === name)
      if (!alert) {
        setError('Alert not found')
        return
      }

      // Create a new alert with "Copy of" prefix
      const newName = `Copy of ${name}`

      // Call API to create the duplicate
      await api.createAlert({
        name: newName,
        source: alert.source,
        source_value: alert.source_value,
        formula: alert.formula,
        notify: alert.notify,
        description: alert.description,
        tags: alert.tags
      })

      await fetchAlerts()
    } catch (err) {
      console.error('Failed to duplicate alert:', err)
      setError('Failed to duplicate alert')
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

  const loadSavedResults = async (alertName: string) => {
    try {
      setLoadingSavedResults(true)
      const response = await api.getAlertResults(alertName, 10)
      setSavedResults(response.results || [])
    } catch (err) {
      console.error('Failed to load saved results:', err)
    } finally {
      setLoadingSavedResults(false)
    }
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

  const getDaysForTimeframe = (tf: '1W' | '1M' | '3M' | 'YTD' | 'ALL') => {
    switch (tf) {
      case '1W':
        return 7
      case '1M':
        return 30
      case '3M':
        return 90
      case 'YTD':
        return 365
      case 'ALL':
        return 1825
      default:
        return 30
    }
  }

  const loadChartsData = async () => {
    if (!sortedResults || sortedResults.length === 0) {
      console.log('No results to load charts for')
      setLoadingCharts(false)
      return
    }

    setLoadingCharts(true)
    setHistoricalData({})
    const data: { [ticker: string]: any[] } = {}

    // Load full historical data like ScreenerDetail does (5 years for timeframe filtering)
    for (const row of sortedResults) {
      const ticker = row.ticker
      if (!data[ticker]) {
        try {
          console.log(`Loading chart data for ${ticker}...`)
          const response = await api.getHistoricalData(ticker, 1825) // ~5 years

          if (response && response.data) {
            // Pass raw data - ResultsWidget will handle transformation
            data[ticker] = response.data
            console.log(`✓ Loaded ${data[ticker].length} rows for ${ticker}`)
          } else {
            data[ticker] = []
          }
        } catch (err) {
          console.error(`✗ Failed to load data for ${ticker}:`, err instanceof Error ? err.message : err)
          data[ticker] = []
        }
      }
    }

    console.log('Chart data loaded for', Object.keys(data).length, 'tickers')
    setHistoricalData(data)
    setLoadingCharts(false)
  }

  // Load chart data when switching to charts view (same as ScreenerDetail)
  useEffect(() => {
    if (resultViewMode === 'charts' && sortedResults && sortedResults.length > 0 && Object.keys(historicalData).length === 0) {
      console.log('Loading chart data for', sortedResults.length, 'results')
      loadChartsData()
    }
  }, [resultViewMode, sortedResults.length])

  // Handle ESC key to close chart modal
  useEffect(() => {
    const handleEscKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && selectedTickerForChart) {
        setSelectedTickerForChart(null)
      }
    }

    window.addEventListener('keydown', handleEscKey)
    return () => window.removeEventListener('keydown', handleEscKey)
  }, [selectedTickerForChart])

  const currentAlert = paramName ? alerts.find((a) => a.name === paramName) : null

  // Extract indicator names from alert formula
  const getFormulaIndicators = (formula: string): Set<string> => {
    const indicators = new Set<string>()
    // Match patterns like: word_number, word_number_word, etc (indicator names)
    // Exclude common keywords: and, or, not, ==, !=, >, <, >=, <=, true, false
    const regex = /\b([a-z_]+(?:_\d+)?(?:_[a-z]+)*)\b/gi
    let match
    while ((match = regex.exec(formula)) !== null) {
      const word = match[1].toLowerCase()
      // Filter out operators and common keywords
      if (![
        'and', 'or', 'not', 'true', 'false',
        'data', 'index', 'ticker', 'company', 'date', 'timestamp',
        'open', 'high', 'low', 'close', 'volume', 'dividends', 'stock', 'splits'
      ].includes(word) && !word.match(/^(==|!=|>|<|>=|<=)$/)) {
        indicators.add(word)
      }
    }
    return indicators
  }

  // Filter chart data by selected timeframe
  const filterDataByTimeframe = (data: any[], timeframe: '1W' | '1M' | '3M' | 'YTD' | 'ALL') => {
    if (!data || data.length === 0) return []

    const today = new Date()
    let cutoffDate = new Date()

    switch (timeframe) {
      case '1W':
        cutoffDate.setDate(today.getDate() - 7)
        break
      case '1M':
        cutoffDate.setMonth(today.getMonth() - 1)
        break
      case '3M':
        cutoffDate.setMonth(today.getMonth() - 3)
        break
      case 'YTD':
        cutoffDate = new Date(today.getFullYear(), 0, 1)
        break
      case 'ALL':
        return data // Return all data
    }

    return data.filter(point => {
      const pointDate = new Date(point.date)
      return pointDate >= cutoffDate
    })
  }

  // Get columns to display (ticker, company_name, then formula indicators, then other columns)
  const getDisplayColumns = (): string[] => {
    if (!sortedResults.length || !sortedResults[0]) return []

    const allKeys = Object.keys(sortedResults[0])
    const formulaIndicators = currentAlert ? getFormulaIndicators(currentAlert.formula) : new Set()

    // Build column order: ticker, company_name, then formula indicators, then others
    const ordered: string[] = []

    // Add ticker and company_name first
    if (allKeys.includes('ticker')) ordered.push('ticker')
    if (allKeys.includes('company_name')) ordered.push('company_name')

    // Add formula indicators in order they appear
    formulaIndicators.forEach(ind => {
      if (allKeys.includes(ind) && !ordered.includes(ind)) {
        ordered.push(ind)
      }
    })

    // Add remaining columns (skip already added)
    allKeys.forEach(key => {
      if (!ordered.includes(key) && !['Index', 'Dividends', 'Stock Splits'].includes(key)) {
        ordered.push(key)
      }
    })

    return ordered
  }

  const handleNotifyConversation = async () => {
    if (!currentAlert || !sortedResults.length) return

    try {
      // Format message with alert name and tickers
      // Signal: ⚠️ alert_name
      const signalLine = `⚠️ ${currentAlert.name}`

      // Format tickers with arrow: ◀ TICKER
      const tickerLines = sortedResults
        .map(r => `◀ ${r.ticker}`)
        .join('\n')

      // Create message with signal and tickers
      const messageContent = `${signalLine}\n${tickerLines}`

      // Get only the visible columns
      const displayColumns = getDisplayColumns()

      // Filter results to only include visible columns
      const filteredResults = sortedResults.map(row => {
        const filtered: any = {}
        displayColumns.forEach(col => {
          if (col in row) {
            filtered[col] = row[col]
          }
        })
        return filtered
      })

      // Send message to conversation with results data and widget info
      await api.sendConversationMessage({
        text: messageContent,
        widget: 'results_widget',
        data: {
          results: filteredResults,
          alert_name: currentAlert.name,
          alert_formula: currentAlert.formula,
          historicalData,
          chartTimeframe,
          columnInfo: displayColumns,
        },
      })
      // Show success message
      alert('Results sent to conversation!')
    } catch (err) {
      console.error('Failed to send to conversation:', err)
      alert('Failed to send to conversation')
    }
  }

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
                      onClick={() => {
                        navigate(`/alerts/${alert.name}`)
                        loadSavedResults(alert.name)
                      }}
                      className="bg-slate-900 border border-slate-800 rounded-lg p-4 cursor-pointer hover:border-purple-500 transition"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-semibold text-white truncate">{alert.name}</h3>
                        <span
                          className={`text-xs px-2 py-1 rounded ${
                            alert.enabled === 'true' || alert.enabled === true
                              ? 'bg-green-900/30 text-green-400'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {alert.enabled === 'true' || alert.enabled === true ? 'Enabled' : 'Disabled'}
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
                      onClick={() => navigate('/alerts')}
                      className="text-slate-400 hover:text-slate-200"
                    >
                      ✕
                    </button>
                  </div>

                  {editMode ? (
                    <form className="space-y-4">
                      <div>
                        <label className="block text-sm text-slate-400 mb-2">Name</label>
                        <input
                          type="text"
                          name="name"
                          value={formData.name || currentAlert?.name || ''}
                          onChange={handleFormChange}
                          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                          placeholder="Alert name"
                        />
                      </div>

                      <div>
                        <label className="block text-sm text-slate-400 mb-2">Source</label>
                        <select
                          name="source"
                          value={formData.source || currentAlert?.source || ''}
                          onChange={handleFormChange}
                          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                        >
                          <option value="">Select source...</option>
                          <option value="universe">Universe</option>
                          <option value="ticker">Ticker</option>
                          <option value="tickers">Tickers</option>
                          <option value="portfolio">Portfolio</option>
                          <option value="all_portfolios">All Portfolios</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm text-slate-400 mb-2">
                          {(formData.source || currentAlert?.source) === 'universe' ? 'Universe' : 'Source Value'}
                        </label>
                        {(formData.source || currentAlert?.source) === 'universe' ? (
                          <select
                            name="source_value"
                            value={formData.source_value || currentAlert?.source_value || ''}
                            onChange={handleFormChange}
                            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                          >
                            <option value="">Select universe...</option>
                            <option value="cac40">CAC 40</option>
                            <option value="srd">SRD</option>
                            <option value="enx_large">Euronext Large</option>
                            <option value="enx_mid">Euronext Mid</option>
                            <option value="enx_small">Euronext Small</option>
                            <option value="nasdaq_100">Nasdaq 100</option>
                            <option value="nasdaq_tech">Nasdaq Tech</option>
                            <option value="etf_pea">ETF PEA</option>
                            <option value="etf_fr">ETF FR</option>
                          </select>
                        ) : (
                          <input
                            type="text"
                            name="source_value"
                            value={formData.source_value || currentAlert?.source_value || ''}
                            onChange={handleFormChange}
                            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                            placeholder={
                              (formData.source || currentAlert?.source) === 'ticker'
                                ? 'e.g., AAPL, AF.PA'
                                : (formData.source || currentAlert?.source) === 'tickers'
                                ? 'e.g., AAPL,AF.PA,MSFT'
                                : (formData.source || currentAlert?.source) === 'portfolio'
                                ? 'e.g., my_portfolio'
                                : 'Enter source value'
                            }
                          />
                        )}
                      </div>

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
                          checked={
                            formData.enabled !== undefined
                              ? typeof formData.enabled === 'string'
                                ? formData.enabled === 'true'
                                : formData.enabled
                              : currentAlert?.enabled === 'true' || currentAlert?.enabled === true
                          }
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
                        <div className="text-sm text-slate-500">Name</div>
                        <div className="text-white font-medium mt-1">{currentAlert?.name}</div>
                      </div>

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
                        <div className={`text-white font-medium mt-1 ${currentAlert?.enabled === 'true' || currentAlert?.enabled === true ? 'text-green-400' : 'text-red-400'}`}>
                          {currentAlert?.enabled === 'true' || currentAlert?.enabled === true ? '✓ Enabled' : '✗ Disabled'}
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
                          onClick={() => handleNotifyConversation()}
                          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded font-medium transition"
                          title="Send to conversation"
                        >
                          🔔 Notify
                        </button>
                        <button
                          type="button"
                          onClick={() => duplicateAlert(currentAlert?.name!)}
                          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium transition"
                        >
                          📋 Duplicate
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

                {/* Right: Results History (1 column) */}
                <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex flex-col">
                  {/* Results History */}
                  <div className="flex-1 overflow-y-auto">
                    <div className="p-4 border-t border-slate-700">
                      <h3 className="text-sm font-semibold text-slate-400 mb-2">History</h3>
                      {loadingSavedResults ? (
                        <div className="text-center py-4 text-slate-500">
                          <p className="text-xs">Loading history...</p>
                        </div>
                      ) : savedResults.length === 0 ? (
                        <div className="text-center py-4 text-slate-500">
                          <p className="text-xs">No results yet</p>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {savedResults.map((result, idx) => {
                            const date = new Date(result.evaluated_at)
                            const timeStr = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
                            const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                            // Generate result ID matching backend format: YYYYMMDD_HHMMSS
                            const year = date.getFullYear()
                            const month = String(date.getMonth() + 1).padStart(2, '0')
                            const day = String(date.getDate()).padStart(2, '0')
                            const hours = String(date.getHours()).padStart(2, '0')
                            const minutes = String(date.getMinutes()).padStart(2, '0')
                            const seconds = String(date.getSeconds()).padStart(2, '0')
                            const resultId = `${year}${month}${day}_${hours}${minutes}${seconds}`
                            const isSelected = paramResultId === resultId
                            return (
                              <div
                                key={idx}
                                className={`p-2 rounded border text-xs transition ${
                                  isSelected
                                    ? 'bg-purple-900/30 border-purple-600'
                                    : 'bg-slate-800/50 border-slate-700 hover:border-slate-600'
                                }`}
                              >
                                <div className="flex items-center justify-between gap-2">
                                  <div
                                    className="flex-1 cursor-pointer"
                                    onClick={() => {
                                      navigate(`/alerts/${paramName}/${resultId}`)
                                      setRunResults(result)
                                    }}
                                  >
                                    <div className={result.matched ? 'text-green-400' : 'text-slate-400'}>
                                      {result.matched ? '✓' : '✗'} {result.matches?.length || 0} matches
                                    </div>
                                    <div className="text-slate-500 text-xs mt-1">
                                      {dateStr} {timeStr}
                                    </div>
                                  </div>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      if (confirm('Delete this result?')) {
                                        api.deleteAlertResult(paramName!, resultId).then(() => {
                                          loadSavedResults(paramName!)
                                        }).catch(err => console.error('Failed to delete result:', err))
                                      }
                                    }}
                                    className="text-slate-500 hover:text-red-400 transition flex-shrink-0"
                                    title="Delete this result"
                                  >
                                    ✕
                                  </button>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Results Table (Bottom) */}
              {currentAlert && runResults && runResults.matches && runResults.matches.length > 0 && (
                <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex flex-col flex-1 min-h-0">
                  {/* Results Header - Same as ScreenerDetail */}
                  <div className="px-6 py-4 border-b border-slate-800">
                    <div className="flex items-center justify-between gap-4">
                      {/* Results Title */}
                      <h2 className="text-lg font-semibold text-white whitespace-nowrap">
                        Results ({sortedResults.length} of {runResults?.matches?.length || 0} matches)
                      </h2>

                      {/* Search Input */}
                      <input
                        type="text"
                        placeholder="Search results..."
                        value={resultSearchQuery}
                        onChange={(e) => setResultSearchQuery(e.target.value)}
                        className="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-slate-600"
                      />

                      {/* Timeframe Selector - shown only in charts view */}
                      {resultViewMode === 'charts' && (
                        <select
                          value={chartTimeframe}
                          onChange={(e) => setChartTimeframe(e.target.value as '1W' | '1M' | '3M' | 'YTD' | 'ALL')}
                          className="px-4 py-1.5 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:border-slate-600 transition font-medium text-sm"
                        >
                          <option value="1W">1W</option>
                          <option value="1M">1M</option>
                          <option value="3M">3M</option>
                          <option value="YTD">YTD</option>
                          <option value="ALL">ALL</option>
                        </select>
                      )}

                      {/* Table/Charts Toggle - Same as ScreenerDetail */}
                      <div className="flex gap-2 bg-slate-800 border border-slate-700 rounded-lg p-1">
                        <button
                          onClick={() => {
                            setResultViewMode('table')
                            if (paramResultId) {
                              navigate(`/alerts/${paramName}/${paramResultId}`)
                            } else {
                              navigate(`/alerts/${paramName}`)
                            }
                          }}
                          className={`px-4 py-1.5 rounded transition font-medium text-sm whitespace-nowrap ${
                            resultViewMode === 'table'
                              ? 'bg-purple-600 text-white'
                              : 'text-slate-400 hover:text-slate-300'
                          }`}
                        >
                          📊 Table
                        </button>
                        <button
                          onClick={() => {
                            setResultViewMode('charts')
                            if (paramResultId) {
                              navigate(`/alerts/${paramName}/${paramResultId}/charts`)
                            } else {
                              navigate(`/alerts/${paramName}/charts`)
                            }
                          }}
                          className={`px-4 py-1.5 rounded transition font-medium text-sm whitespace-nowrap ${
                            resultViewMode === 'charts'
                              ? 'bg-purple-600 text-white'
                              : 'text-slate-400 hover:text-slate-300'
                          }`}
                        >
                          📈 Charts
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Table View - Same as ScreenerDetail, with formula indicators */}
                  {resultViewMode === 'table' && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-slate-800/50 border-b border-slate-800">
                          <tr>
                            {getDisplayColumns().map((key) => (
                              <th
                                key={key}
                                onClick={() => {
                                  if (resultSortColumn === key) {
                                    setResultSortDirection(resultSortDirection === 'asc' ? 'desc' : 'asc')
                                  } else {
                                    setResultSortColumn(key)
                                    setResultSortDirection('asc')
                                  }
                                }}
                                className="px-6 py-3 text-left text-slate-300 font-medium cursor-pointer hover:bg-slate-700/50 transition"
                              >
                                <div className="flex items-center gap-2">
                                  {key}
                                  {resultSortColumn === key && (
                                    <span className="text-xs text-slate-400">
                                      {resultSortDirection === 'asc' ? '↑' : '↓'}
                                    </span>
                                  )}
                                </div>
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                          {sortedResults.map((row, idx) => (
                            <tr
                              key={idx}
                              onClick={() => setSelectedTickerForChart(row.ticker)}
                              className="hover:bg-slate-800/50 cursor-pointer transition"
                            >
                              {getDisplayColumns().map((key) => {
                                const value = row[key]
                                let displayValue = String(value || '')

                                // Check if this is a date/timestamp column
                                const isDateColumn = key.toLowerCase().includes('date') || key.toLowerCase().includes('timestamp') || key.toLowerCase().includes('time')
                                if (isDateColumn && value) {
                                  try {
                                    const date = new Date(String(value))
                                    if (!isNaN(date.getTime())) {
                                      const day = String(date.getDate()).padStart(2, '0')
                                      const month = String(date.getMonth() + 1).padStart(2, '0')
                                      const year = String(date.getFullYear()).slice(-2)
                                      displayValue = `${day}/${month}/${year}`
                                    }
                                  } catch (e) {
                                    // If date parsing fails, use original value
                                  }
                                } else {
                                  // Numeric formatting
                                  const numValue = typeof value === 'number' ? value : parseFloat(String(value || 0))
                                  if (!isNaN(numValue)) {
                                    // Format volume with 0 decimal places
                                    if (key.toLowerCase().includes('volume') || key.toLowerCase().includes('vol')) {
                                      displayValue = numValue.toFixed(0)
                                    } else {
                                      // Format other numbers with 3 decimal places
                                      displayValue = numValue.toFixed(3)
                                    }
                                  }
                                }

                                return (
                                  <td key={key} className="px-6 py-3 text-slate-300">
                                    {displayValue}
                                  </td>
                                )
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Charts View - Same as ScreenerDetail */}
                  {resultViewMode === 'charts' && (
                    <div className="p-6">
                      {sortedResults.length === 0 ? (
                        <div className="text-center py-12 text-slate-400">
                          No matches in this result
                        </div>
                      ) : loadingCharts ? (
                        <div className="text-center py-12 text-slate-400">
                          Loading price history for {sortedResults.length} tickers...
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                          {sortedResults.map((match: any) => {
                            const ticker = match.ticker
                            const allData = historicalData[ticker] || []
                            // Filter data by selected timeframe
                            const chartData = filterDataByTimeframe(allData, chartTimeframe)

                            // Calculate change percentage based on filtered data
                            let changePercent = 0
                            let isPositive = false
                            if (chartData.length > 1) {
                              const oldPrice = chartData[0]?.close || 0
                              const newPrice = chartData[chartData.length - 1]?.close || 0
                              if (oldPrice) {
                                changePercent = ((newPrice - oldPrice) / oldPrice) * 100
                                isPositive = changePercent >= 0
                              }
                            }

                            return (
                              <div
                                key={ticker}
                                onClick={() => setSelectedTickerForChart(ticker)}
                                className="bg-slate-800 rounded-lg overflow-hidden border border-slate-700 flex flex-col h-full cursor-pointer hover:border-slate-600 transition"
                              >
                                <div className="p-4 border-b border-slate-700 flex-shrink-0 bg-slate-900/50">
                                  <div className="flex items-start justify-between gap-4">
                                    {/* Left: Company name and ticker */}
                                    <div className="flex-1 min-w-0">
                                      {match.company_name && match.company_name !== ticker ? (
                                        <>
                                          <h3 className="text-lg font-bold text-white truncate">
                                            {match.company_name}
                                          </h3>
                                          <p className="text-sm text-slate-400 mt-1">{ticker}</p>
                                        </>
                                      ) : (
                                        <h3 className="text-lg font-bold text-white truncate">
                                          {ticker}
                                        </h3>
                                      )}
                                    </div>

                                    {/* Right: Change % and timeframe */}
                                    <div className="flex flex-col items-end flex-shrink-0">
                                      <div className={`text-lg font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                                        {isPositive ? '+' : ''}{changePercent.toFixed(1)}%
                                      </div>
                                      <div className="text-xs text-slate-400 mt-1">{chartTimeframe} Change</div>
                                    </div>
                                  </div>
                                </div>
                                <div className="flex-1 p-4 bg-slate-900/50 flex flex-col justify-center min-h-0">
                                  {chartData && chartData.length > 0 ? (
                                    <CardChart
                                      ticker={ticker}
                                      data={chartData}
                                    />
                                  ) : (
                                    <div className="flex items-center justify-center text-center text-slate-500">
                                      <div>
                                        <p className="text-xs">No data available</p>
                                        <p className="text-xs mt-2 text-slate-600">{historicalData[ticker] ? 'Loading...' : 'Waiting for data'}</p>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      )}
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
                <label className="block text-sm font-medium text-slate-400 mb-2">
                  {newAlertData.source === 'universe' ? 'Universe' : 'Source Value'}
                </label>
                {newAlertData.source === 'universe' ? (
                  <select
                    value={newAlertData.source_value}
                    onChange={(e) => setNewAlertData({ ...newAlertData, source_value: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded focus:outline-none focus:border-purple-500"
                  >
                    <option value="">Select universe...</option>
                    <option value="cac40">CAC 40</option>
                    <option value="srd">SRD</option>
                    <option value="enx_large">Euronext Large</option>
                    <option value="enx_mid">Euronext Mid</option>
                    <option value="enx_small">Euronext Small</option>
                    <option value="nasdaq_100">Nasdaq 100</option>
                    <option value="nasdaq_tech">Nasdaq Tech</option>
                    <option value="etf_pea">ETF PEA</option>
                    <option value="etf_fr">ETF FR</option>
                  </select>
                ) : (
                  <input
                    type="text"
                    value={newAlertData.source_value}
                    onChange={(e) => setNewAlertData({ ...newAlertData, source_value: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded focus:outline-none focus:border-purple-500"
                    placeholder={
                      newAlertData.source === 'ticker'
                        ? 'e.g., AAPL, AF.PA'
                        : newAlertData.source === 'tickers'
                        ? 'e.g., AAPL,AF.PA,MSFT'
                        : newAlertData.source === 'portfolio'
                        ? 'e.g., my_portfolio'
                        : 'Enter source value'
                    }
                  />
                )}
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

      {/* Trading Chart Widget Modal */}
      {selectedTickerForChart && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-950 border border-slate-800 rounded-lg w-full h-[90vh] max-w-7xl flex flex-col">
            {/* Header with Close Button */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 flex-shrink-0">
              <h2 className="text-2xl font-bold text-white">{selectedTickerForChart}</h2>
              <button
                onClick={() => setSelectedTickerForChart(null)}
                className="text-slate-400 hover:text-white transition text-2xl"
              >
                ✕
              </button>
            </div>

            {/* Chart Widget with Controls */}
            <div className="flex-1 overflow-hidden">
              <TradingChartWidget
                ticker={selectedTickerForChart}
                showControls={true}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

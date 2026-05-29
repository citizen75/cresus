import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import TradingChart from '@/components/TradingChart'

interface ScreenerConfig {
  name: string
  source?: string
  tickers?: string[]
  indicators?: string[]
  formula?: string
  description?: string
}

interface ScreenerResult {
  result_id: string
  timestamp: string
  matches?: any[]
}

export default function ScreenerDetail() {
  const { name: paramName } = useParams<{ name?: string }>()
  const navigate = useNavigate()
  const [screener, setScreener] = useState<ScreenerConfig | null>(null)
  const [results, setResults] = useState<ScreenerResult[]>([])
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null)
  const [selectedResult, setSelectedResult] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [formData, setFormData] = useState<Partial<ScreenerConfig>>({})
  const [selectedRow, setSelectedRow] = useState<any | null>(null)
  const [chartData, setChartData] = useState<any[]>([])
  const [chartLoading, setChartLoading] = useState(false)

  const [universes] = useState([
    'cac40',
    'srd',
    'enx_large',
    'enx_mid',
    'enx_small',
    'nasdaq_100',
    'nasdaq_tech',
    'etf_pea',
    'etf_fr',
  ])

  useEffect(() => {
    if (paramName) {
      loadScreener()
      loadResults()
    }
  }, [paramName])

  // Auto-load the latest result when results are loaded
  useEffect(() => {
    if (results.length > 0 && !selectedResultId) {
      const latestResult = results[0]
      setSelectedResultId(latestResult.result_id)
      loadResult(latestResult.result_id)
    }
  }, [results, selectedResultId])

  // Load chart data when a row is selected
  useEffect(() => {
    if (selectedRow && (selectedRow.ticker || selectedRow.symbol)) {
      loadChartData(selectedRow.ticker || selectedRow.symbol)
    }
  }, [selectedRow])

  const loadScreener = async () => {
    if (!paramName) return
    try {
      const response = await api.getScreener(paramName)
      setScreener(response.screener)
      setFormData(response.screener)
      setError(null)
    } catch (err) {
      setError('Failed to load screener')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const loadResults = async () => {
    if (!paramName) return
    try {
      const response = await api.listScreenerResults(paramName)
      setResults(response.results || [])
    } catch (err) {
      console.error(err)
    }
  }

  const handleRun = async () => {
    if (!paramName) return
    try {
      setRunning(true)
      setError(null)
      const response = await api.runScreener(paramName)

      // Reload results list
      await loadResults()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run screener')
      console.error(err)
    } finally {
      setRunning(false)
    }
  }

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.currentTarget
    setFormData({
      ...formData,
      [name]: value,
    })
  }

  const handleSave = async (e: React.FormEvent) => {
    if (!paramName) return
    e.preventDefault()
    try {
      await api.updateScreener(paramName, {
        source: formData.source,
        formula: formData.formula,
        description: formData.description,
      })
      setEditMode(false)
      await loadScreener()
    } catch (err) {
      setError('Failed to update screener')
      console.error(err)
    }
  }

  const loadResult = async (resultId: string) => {
    if (!paramName) return
    try {
      const response = await api.getScreenerResult(paramName, resultId)
      setSelectedResult(response.data || [])
      setSelectedResultId(resultId)
    } catch (err) {
      setError('Failed to load result')
      console.error(err)
    }
  }

  const handleDeleteResult = async (resultId: string) => {
    if (!paramName) return
    if (!confirm('Delete this result?')) return

    try {
      await api.deleteScreenerResult(paramName, resultId)
      if (selectedResultId === resultId) {
        setSelectedResult([])
        setSelectedResultId(null)
      }
      await loadResults()
    } catch (err) {
      setError('Failed to delete result')
      console.error(err)
    }
  }

  const handleClearResults = async () => {
    if (!paramName) return
    if (!confirm('Clear ALL results for this screener?')) return

    try {
      await api.clearScreenerResults(paramName)
      setSelectedResult([])
      setSelectedResultId(null)
      await loadResults()
    } catch (err) {
      setError('Failed to clear results')
      console.error(err)
    }
  }

  const loadChartData = async (ticker: string) => {
    try {
      setChartLoading(true)
      const response = await api.getHistoricalData(ticker, 90)
      if (response && response.data) {
        const chartDataPoints = response.data.map((item: any) => ({
          date: item.Date || item.timestamp,
          close: parseFloat(item.Close || item.close || 0),
          volume: parseFloat(item.Volume || item.volume || 0),
        }))
        setChartData(chartDataPoints.reverse())
      }
    } catch (err) {
      console.error('Failed to load chart data:', err)
      setChartData([])
    } finally {
      setChartLoading(false)
    }
  }

  if (!paramName) {
    return (
      <div className="text-center py-12">
        <div className="text-red-400">No screener specified</div>
        <button
          onClick={() => navigate('/screener')}
          className="mt-4 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded"
        >
          Back to Screeners
        </button>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="text-slate-500">Loading screener...</div>
      </div>
    )
  }

  if (!screener) {
    return (
      <div className="text-center py-12">
        <div className="text-red-400">Screener not found</div>
        <button
          onClick={() => navigate('/screener')}
          className="mt-4 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded"
        >
          Back to Screeners
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate('/screener')}
            className="text-purple-400 hover:text-purple-300 text-sm mb-2"
          >
            ← Back to Screeners
          </button>
          <h1 className="text-3xl font-bold text-white">{screener.name}</h1>
          {screener.description && (
            <p className="text-sm text-slate-400 mt-1">{screener.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          {editMode ? (
            <>
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition"
              >
                Save
              </button>
              <button
                onClick={() => setEditMode(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-medium transition"
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleRun}
                disabled={running}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg font-medium transition"
              >
                {running ? 'Running...' : '▶ Run'}
              </button>
              <button
                onClick={() => setEditMode(true)}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition"
              >
                Edit
              </button>
            </>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-900/20 border border-red-700 text-red-400 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Edit Form */}
      {editMode && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Edit Screener</h2>

          <form onSubmit={handleSave} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Source */}
              <div>
                <label className="block text-sm text-slate-300 mb-2">Source (Universe)</label>
                <select
                  name="source"
                  value={formData.source || screener?.source || ''}
                  onChange={handleFormChange}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                >
                  <option value="">Select universe...</option>
                  {universes.map((u) => (
                    <option key={u} value={u}>
                      {u}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Formula */}
            <div>
              <label className="block text-sm text-slate-300 mb-2">Formula</label>
              <textarea
                name="formula"
                value={formData.formula || screener?.formula || ''}
                onChange={handleFormChange}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500 font-mono"
                placeholder="e.g., rsi_14[0] > 70 and close[0] > ema_20[0]"
                rows={3}
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm text-slate-300 mb-2">Description</label>
              <input
                type="text"
                name="description"
                value={formData.description || screener?.description || ''}
                onChange={handleFormChange}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                placeholder="Optional description"
              />
            </div>

            {/* Buttons */}
            <div className="flex gap-3 pt-4">
              <button
                type="submit"
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded font-medium transition"
              >
                Save
              </button>
              <button
                type="button"
                onClick={() => setEditMode(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium transition"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Configuration and Results Side by Side */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Configuration (Left - 3 columns / 75%) */}
        <div className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Configuration</h2>

          <div className="space-y-4">
            <div>
              <div className="text-slate-500 text-sm">Source</div>
              <div className="text-white font-medium mt-1">{screener.source || '—'}</div>
            </div>

            <div>
              <div className="text-slate-500 text-sm">Formula</div>
              <div className="text-white font-mono text-xs mt-1 break-words">
                {screener.formula || '—'}
              </div>
            </div>

            {screener.indicators && screener.indicators.length > 0 && (
              <div>
                <div className="text-slate-500 text-sm">Indicators</div>
                <div className="text-white text-xs mt-1">
                  {screener.indicators.join(', ')}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Recent Results (Right - 1 column / 25%) */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Recent Results</h2>
            {results.length > 0 && (
              <button
                onClick={handleClearResults}
                className="px-2 py-1 text-xs font-medium text-red-400 hover:text-red-300 rounded transition"
                title="Clear all results"
              >
                Clear All
              </button>
            )}
          </div>

          {results.length === 0 ? (
            <div className="text-center py-6">
              <div className="text-slate-500">No results yet. Run the screener to see results.</div>
            </div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {results.map((result) => (
                <div
                  key={result.result_id}
                  className={`flex items-center justify-between px-4 py-3 rounded-lg border cursor-pointer transition ${
                    selectedResultId === result.result_id
                      ? 'bg-purple-900/30 border-purple-600'
                      : 'bg-slate-800/50 border-slate-700 hover:border-slate-600'
                  }`}
                  onClick={() => loadResult(result.result_id)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-white font-mono text-sm truncate">{result.result_id}</div>
                    <div className="text-xs text-slate-400 mt-1">
                      {new Date(result.timestamp).toLocaleString()}
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDeleteResult(result.result_id)
                    }}
                    className="px-2 py-1 text-red-400 hover:text-red-300 rounded transition ml-2"
                    title="Delete this result"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Results Table */}
      {selectedResult && selectedResult.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-800">
            <h2 className="text-lg font-semibold text-white">Results ({selectedResult.length} matches)</h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-800/50 border-b border-slate-800">
                <tr>
                  {selectedResult.length > 0 &&
                    Object.keys(selectedResult[0]).map((key) => (
                      <th key={key} className="px-6 py-3 text-left text-slate-300 font-medium">
                        {key}
                      </th>
                    ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {selectedResult.map((row, idx) => (
                  <tr
                    key={idx}
                    className="hover:bg-slate-800/50 cursor-pointer transition"
                    onClick={() => setSelectedRow(row)}
                  >
                    {Object.values(row).map((value, colIdx) => (
                      <td key={colIdx} className="px-6 py-3 text-slate-300">
                        {typeof value === 'number' ? value.toFixed(2) : String(value)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Row Details Modal */}
      {selectedRow && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-lg border border-slate-800 w-full max-w-6xl h-screen max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
              <div>
                <h2 className="text-2xl font-bold text-white">
                  {selectedRow.ticker || selectedRow.symbol}
                  <span className="text-lg text-slate-400 ml-2">
                    - Current Price: €{parseFloat(selectedRow.close)?.toFixed(2) || '—'} | Close: €{parseFloat(selectedRow.close)?.toFixed(2) || '—'}
                  </span>
                </h2>
                <p className="text-slate-400 text-sm mt-1">Live Position Analysis</p>
              </div>
              <button
                onClick={() => setSelectedRow(null)}
                className="text-slate-400 hover:text-white transition text-2xl"
              >
                ✕
              </button>
            </div>

            {/* Chart Container */}
            <div className="flex-1 overflow-hidden">
              <TradingChart
                timeframe="1Y"
                title={`${selectedRow.ticker || selectedRow.symbol || 'N/A'} - Position Analysis`}
                ticker={selectedRow.ticker || selectedRow.symbol}
              />
            </div>

            {/* Details Grid Footer */}
            <div className="border-t border-slate-800 bg-slate-800/30 p-4 max-h-32 overflow-y-auto">
              <h3 className="text-sm font-medium text-slate-300 mb-3">Screener Match Details</h3>
              <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {Object.entries(selectedRow).map(([key, value]) => (
                  <div key={key}>
                    <div className="text-slate-500 text-xs font-medium mb-1">{key}</div>
                    <div className="text-white font-mono text-xs">
                      {typeof value === 'number' ? value.toFixed(4) : String(value)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

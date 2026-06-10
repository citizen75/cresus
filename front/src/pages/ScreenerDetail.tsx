import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { useHistoricalDataLoader } from '@/hooks/useHistoricalDataLoader'
import TradingChart from '@/components/TradingChart'
import CardChart from '@/components/CardChart'
import ResultsWidget from '@/components/ResultsWidget'

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
  const { name: paramName, view: viewParam } = useParams<{ name?: string; view?: string }>()
  const navigate = useNavigate()
  const [screener, setScreener] = useState<ScreenerConfig | null>(null)
  const [results, setResults] = useState<ScreenerResult[]>([])
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null)
  const [selectedResult, setSelectedResult] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [loadingResults, setLoadingResults] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [formData, setFormData] = useState<Partial<ScreenerConfig>>({})
  const [selectedRow, setSelectedRow] = useState<any | null>(null)
  const [hoverData, setHoverData] = useState<any | null>(null)
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [sortColumn, setSortColumn] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const [formulaError, setFormulaError] = useState<string | null>(null)
  const [previewResults, setPreviewResults] = useState<any[]>([])
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewMatchCount, setPreviewMatchCount] = useState(0)
  const [previewSearchQuery, setPreviewSearchQuery] = useState<string>('')
  const [previewSortColumn, setPreviewSortColumn] = useState<string | null>(null)
  const [previewSortDirection, setPreviewSortDirection] = useState<'asc' | 'desc'>('asc')
  const [resultViewMode, setResultViewMode] = useState<'table' | 'charts'>(viewParam === 'charts' ? 'charts' : 'table')
  const [historicalData, setHistoricalData] = useState<{ [ticker: string]: any[] }>({})
  const [loadingCharts, setLoadingCharts] = useState(false)
  const [chartTimeframe, setChartTimeframe] = useState<'1W' | '1M' | '3M' | 'YTD' | 'ALL'>('1M')

  // Use centralized data loader
  const { loadData } = useHistoricalDataLoader()

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

  // Filter and sort results
  const filteredAndSortedResults = (() => {
    let filtered = selectedResult.filter((row) => {
      if (!searchQuery.trim()) return true
      const query = searchQuery.toLowerCase()
      return Object.values(row).some((val) =>
        String(val).toLowerCase().includes(query)
      )
    })

    if (sortColumn) {
      filtered.sort((a, b) => {
        const aVal = a[sortColumn]
        const bVal = b[sortColumn]
        const isNumeric = typeof aVal === 'number' && typeof bVal === 'number'

        if (isNumeric) {
          return sortDirection === 'asc' ? aVal - bVal : bVal - aVal
        } else {
          const aStr = String(aVal || '').toLowerCase()
          const bStr = String(bVal || '').toLowerCase()
          return sortDirection === 'asc'
            ? aStr.localeCompare(bStr)
            : bStr.localeCompare(aStr)
        }
      })
    }

    return filtered
  })()

  // Filter and sort preview results
  const filteredAndSortedPreviewResults = (() => {
    let filtered = previewResults.filter((row) => {
      if (!previewSearchQuery.trim()) return true
      const query = previewSearchQuery.toLowerCase()
      return Object.values(row).some((val) =>
        String(val).toLowerCase().includes(query)
      )
    })

    if (previewSortColumn) {
      filtered.sort((a, b) => {
        const aVal = a[previewSortColumn]
        const bVal = b[previewSortColumn]
        const isNumeric = typeof aVal === 'number' && typeof bVal === 'number'

        if (isNumeric) {
          return previewSortDirection === 'asc' ? aVal - bVal : bVal - aVal
        } else {
          const aStr = String(aVal || '').toLowerCase()
          const bStr = String(bVal || '').toLowerCase()
          return previewSortDirection === 'asc'
            ? aStr.localeCompare(bStr)
            : bStr.localeCompare(aStr)
        }
      })
    }

    return filtered
  })()

  const handleColumnSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('asc')
    }
  }

  const handlePreviewColumnSort = (column: string) => {
    if (previewSortColumn === column) {
      setPreviewSortDirection(previewSortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setPreviewSortColumn(column)
      setPreviewSortDirection('asc')
    }
  }

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

  // Formula validation
  useEffect(() => {
    if (!editMode || !formData.formula) {
      setFormulaError(null)
      return
    }

    // Basic syntax validation only
    const validateFormula = () => {
      const formula = (formData.formula || '').trim()

      // Check for common issues
      if (formula.includes('[[') || formula.includes(']]')) {
        return 'Invalid syntax: double brackets not allowed'
      }

      if ((formula.match(/\(/g) || []).length !== (formula.match(/\)/g) || []).length) {
        return 'Invalid syntax: mismatched parentheses'
      }

      return null
    }

    const error = validateFormula()
    setFormulaError(error)
  }, [formData.formula, editMode])

  // Test formula handler
  const handleTestFormula = async () => {
    if (!formData.formula || !formData.source) {
      setFormulaError('Formula and source required')
      return
    }

    try {
      setPreviewLoading(true)
      const response = await api.screenerBuilder(formData.formula, formData.source)

      if (response && response.status === 'success') {
        setPreviewResults(response.matches || [])
        setPreviewMatchCount(response.match_count || 0)
        setFormulaError(null)
      } else {
        setFormulaError(response?.message || 'Screening failed')
        setPreviewResults([])
        setPreviewMatchCount(0)
      }
    } catch (err: any) {
      console.error('Failed to test formula:', err)
      // Extract error detail from API response
      let errorMessage = 'Formula test failed'
      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail
      } else if (err.message) {
        errorMessage = err.message
      }
      setFormulaError(errorMessage)
      setPreviewResults([])
      setPreviewMatchCount(0)
    } finally {
      setPreviewLoading(false)
    }
  }

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
      setLoadingResults(true)
      const response = await api.listScreenerResults(paramName)
      setResults(response.results || [])
    } catch (err) {
      console.error('Failed to load results:', err)
      setError('Failed to load results')
    } finally {
      setLoadingResults(false)
    }
  }

  const handleRun = async () => {
    if (!paramName) return
    try {
      setRunning(true)
      setError(null)
      await api.runScreener(paramName)

      // Reload results list and auto-select the latest
      const resultsResponse = await api.listScreenerResults(paramName)
      const resultsList = resultsResponse.results || []
      setResults(resultsList)

      // Auto-load the latest result
      if (resultsList.length > 0) {
        const latestResult = resultsList[0]
        setSelectedResultId(latestResult.result_id)
        const resultData = await api.getScreenerResult(paramName, latestResult.result_id)
        setSelectedResult(resultData.data || [])
      }
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

  const deleteScreener = async (name: string) => {
    try {
      await api.deleteScreener(name)
      navigate('/screener')
    } catch (err) {
      setError('Failed to delete screener')
      console.error(err)
    }
  }

  const loadChartData = async (ticker: string) => {
    // Chart data is loaded directly by TradingChart component
    // This function is kept for compatibility with useEffect
    void ticker  // Suppress unused parameter warning
  }

  const handleViewModeChange = (mode: 'table' | 'charts') => {
    setResultViewMode(mode)
    if (paramName) {
      navigate(`/screener/${paramName}${mode === 'charts' ? '/charts' : ''}`)
    }
    // ResultsWidget handles data loading via hook when mode changes
  }

  const getDaysForTimeframe = (tf: string) => {
    switch (tf) {
      case '1W': return 7
      case '1M': return 30
      case '3M': return 90
      case 'YTD': return 365
      case 'ALL': return 1825 // ~5 years
      default: return 30
    }
  }

  const filterDataByTimeframe = (data: any[], tf: string) => {
    if (!data || data.length === 0) return data

    let cutoffDate = new Date()

    if (tf === 'YTD') {
      cutoffDate = new Date(cutoffDate.getFullYear(), 0, 1)
    } else if (tf !== 'ALL') {
      const days = getDaysForTimeframe(tf)
      cutoffDate.setDate(cutoffDate.getDate() - days)
    }

    // Filter and sort by date (oldest to newest)
    return data
      .filter((item: any) => {
        const itemDate = new Date(item.date || item.timestamp)
        return tf === 'ALL' || itemDate >= cutoffDate
      })
      .sort((a: any, b: any) => {
        const dateA = new Date(a.date || a.timestamp)
        const dateB = new Date(b.date || b.timestamp)
        return dateA.getTime() - dateB.getTime()
      })
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

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-900/20 border border-red-700 text-red-400 rounded-lg text-sm">
          {error}
        </div>
      )}


      {/* Configuration and Results Side by Side */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Configuration (Left - 3 columns / 75%) */}
        <div className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-6">Configuration</h2>

          <form id="screener-form" onSubmit={handleSave} className="space-y-4">
            <div>
              <div className="text-slate-500 text-sm">Source</div>
              {editMode ? (
                <select
                  name="source"
                  value={formData.source || screener?.source || ''}
                  onChange={handleFormChange}
                  className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                >
                  <option value="">Select universe...</option>
                  {universes.map((u) => (
                    <option key={u} value={u}>
                      {u}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="text-white font-medium mt-1">{screener.source || '—'}</div>
              )}
            </div>

            <div>
              <div className="text-slate-500 text-sm">Formula</div>
              {editMode ? (
                <>
                  <textarea
                    name="formula"
                    value={formData.formula || screener?.formula || ''}
                    onChange={handleFormChange}
                    className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500 font-mono"
                    placeholder="e.g., sha_10_up[0] == 1 && rsi_14 > 50"
                    rows={3}
                  />

                  {/* Formula Validation */}
                  {formData.formula && (
                    <div className="mt-4 p-3 rounded border">
                      {formulaError ? (
                        <div className="bg-red-900/20 border border-red-700 text-red-400 text-sm">
                          <div className="font-medium">Formula Error</div>
                          <div className="text-xs mt-1">{formulaError}</div>
                        </div>
                      ) : (
                        <div className="bg-green-900/20 border border-green-700 text-green-400 text-sm">
                          <div className="font-medium">✓ Formula syntax is valid</div>
                          <div className="text-xs mt-1">
                            {previewLoading ? 'Loading preview...' : `${previewMatchCount} matches found`}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="text-white font-mono text-xs mt-1 break-words">
                  {screener.formula || '—'}
                </div>
              )}
            </div>

            {screener.indicators && screener.indicators.length > 0 && (
              <div>
                <div className="text-slate-500 text-sm">Indicators</div>
                <div className="text-white text-xs mt-1">
                  {screener.indicators.join(', ')}
                </div>
              </div>
            )}

            {/* Action Buttons - Bottom of Form */}
            <div className="flex gap-3 pt-6 border-t border-slate-700">
              {editMode && (
                <>
                  <button
                    type="button"
                    onClick={handleTestFormula}
                    disabled={previewLoading || !formData.formula || !formData.source}
                    className="px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white rounded font-medium transition"
                  >
                    {previewLoading ? 'Testing...' : '🧪 Test Formula'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditMode(false)}
                    className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded font-medium transition text-sm"
                    title="Cancel editing"
                  >
                    ✕ Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium transition text-sm"
                    title="Save changes"
                  >
                    ✓ Save
                  </button>
                </>
              )}
              {!editMode && (
                <>
                  <button
                    type="button"
                    onClick={handleRun}
                    disabled={loadingResults}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded font-medium transition text-sm"
                    title="Run screener"
                  >
                    {loadingResults ? '⟳ Running...' : '▶ Run'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditMode(true)}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium transition text-sm"
                    title="Edit screener"
                  >
                    ✎ Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (confirm(`Delete screener "${paramName}"?`)) {
                        deleteScreener(paramName!)
                      }
                    }}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded font-medium transition text-sm"
                    title="Delete screener"
                  >
                    🗑 Delete
                  </button>
                </>
              )}
            </div>
          </form>
        </div>

        {/* Recent Results (Right - 1 column / 25%) */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Recent Results</h2>

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

      {/* Results Loading State */}
      {loadingResults && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-12 text-center">
          <div className="text-slate-400">Loading results...</div>
        </div>
      )}

      {/* No Results Message */}
      {!loadingResults && results.length === 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-12 text-center">
          <div className="text-slate-400">No results available. Click "▶ Run" to execute the screener.</div>
        </div>
      )}

      {/* Results Widget */}
      {!loadingResults && results.length > 0 && selectedResult !== null && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex flex-col">
          <ResultsWidget
            data={filteredAndSortedResults}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            sortColumn={sortColumn}
            onSortChange={(col) => {
              if (sortColumn === col) {
                setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
              } else {
                setSortColumn(col)
                setSortDirection('asc')
              }
            }}
            sortDirection={sortDirection}
            onSortDirectionChange={setSortDirection}
            historicalData={historicalData}
            onSetHistoricalData={setHistoricalData}
            loadingCharts={loadingCharts}
            chartTimeframe={chartTimeframe}
            onChartTimeframeChange={setChartTimeframe}
            viewMode={resultViewMode}
            onViewModeChange={setResultViewMode}
            onGetHistoricalData={api.getHistoricalData.bind(api)}
          />
        </div>
      )}

      {/* Preview Results Section (shown when editing and test was run) */}
      {editMode && previewResults.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-800">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">Test Results ({filteredAndSortedPreviewResults.length} of {previewMatchCount})</h2>
            </div>
            <input
              type="text"
              placeholder="Search results..."
              value={previewSearchQuery}
              onChange={(e) => setPreviewSearchQuery(e.target.value)}
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-slate-600"
            />
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-800/50 border-b border-slate-800">
                <tr>
                  {previewResults.length > 0 &&
                    Object.keys(previewResults[0]).map((key) => (
                      <th
                        key={key}
                        onClick={() => handlePreviewColumnSort(key)}
                        className="px-6 py-3 text-left text-slate-300 font-medium cursor-pointer hover:bg-slate-700/50 transition"
                      >
                        <div className="flex items-center gap-2">
                          {key}
                          {previewSortColumn === key && (
                            <span className="text-xs text-slate-400">
                              {previewSortDirection === 'asc' ? '↑' : '↓'}
                            </span>
                          )}
                        </div>
                      </th>
                    ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {filteredAndSortedPreviewResults.map((row, idx) => (
                  <tr
                    key={idx}
                    className="hover:bg-slate-800/50 cursor-pointer transition"
                    onClick={() => {
                      console.log('Preview row clicked:', row)
                      setSelectedRow(row)
                    }}
                  >
                    {Object.entries(row).map(([key, value], colIdx) => {
                      let displayValue = String(value || '')
                      const numValue = typeof value === 'number' ? value : parseFloat(String(value || 0))

                      if (!isNaN(numValue)) {
                        if (key.toLowerCase().includes('volume') || key.toLowerCase().includes('vol')) {
                          displayValue = numValue.toFixed(0)
                        } else {
                          displayValue = numValue.toFixed(3)
                        }
                      }
                      return (
                        <td key={colIdx} className="px-6 py-3 text-slate-300">
                          {displayValue}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Row Details Modal */}
      {selectedRow && (() => {
        console.log('Modal rendering with selectedRow:', selectedRow)
        return (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-lg border border-slate-800 w-full max-w-6xl h-screen max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
              <div>
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold text-white">
                    {(selectedRow.company_name || selectedRow.company || selectedRow.name) && (
                      <span className="text-slate-400 font-normal">{selectedRow.company_name || selectedRow.company || selectedRow.name} </span>
                    )}
                    {selectedRow.ticker || selectedRow.symbol}
                  </h2>
                  <div className="text-sm text-slate-400 font-mono">
                    {(hoverData?.open || selectedRow.open) && (
                      <>
                        <span className="text-slate-400">O </span>
                        <span className="text-white">{parseFloat(hoverData?.open || selectedRow.open)?.toFixed(3) || '—'}</span>
                      </>
                    )}
                    {(hoverData?.high || selectedRow.high) && (
                      <>
                        <span className="text-slate-400 ml-3">H </span>
                        <span className="text-white">{parseFloat(hoverData?.high || selectedRow.high)?.toFixed(3) || '—'}</span>
                      </>
                    )}
                    {(hoverData?.low || selectedRow.low) && (
                      <>
                        <span className="text-slate-400 ml-3">L </span>
                        <span className="text-white">{parseFloat(hoverData?.low || selectedRow.low)?.toFixed(3) || '—'}</span>
                      </>
                    )}
                    {(hoverData?.close || selectedRow.close) && (
                      <>
                        <span className="text-slate-400 ml-3">C </span>
                        <span className="text-white">{parseFloat(hoverData?.close || selectedRow.close)?.toFixed(3) || '—'}</span>
                      </>
                    )}
                    {(hoverData?.volume || selectedRow.volume) && (
                      <>
                        <span className="text-slate-400 ml-3">Vol </span>
                        <span className="text-white">{(parseFloat(hoverData?.volume || selectedRow.volume) / 1000)?.toFixed(1)}K</span>
                      </>
                    )}
                    {(() => {
                      const dataToUse = hoverData || selectedRow
                      let variationPct = parseFloat(dataToUse.daily_change_pct || dataToUse.variation_pct || dataToUse.pct_change || 0)
                      if (!variationPct && dataToUse.open && dataToUse.close) {
                        variationPct = ((parseFloat(dataToUse.close) - parseFloat(dataToUse.open)) / parseFloat(dataToUse.open)) * 100
                      }
                      return variationPct ? (
                        <span className={`ml-3 ${variationPct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {variationPct >= 0 ? '+' : ''}{variationPct?.toFixed(2)}%
                        </span>
                      ) : null
                    })()}
                  </div>
                </div>
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
                onCursorMove={setHoverData}
              />
            </div>
          </div>
        </div>
        )
      })()}
    </div>
  )
}

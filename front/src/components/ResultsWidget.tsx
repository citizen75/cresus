import { useState, useEffect } from 'react'
import CardChart from './CardChart'
import TradingChartWidget from './TradingChartWidget'
import { api } from '@/services/api'

interface ResultsWidgetProps {
  data: any[] // Array of result objects
  searchQuery: string
  onSearchChange: (query: string) => void
  sortColumn: string | null
  onSortChange: (column: string) => void
  sortDirection: 'asc' | 'desc'
  onSortDirectionChange: (direction: 'asc' | 'desc') => void
  historicalData?: { [ticker: string]: any[] }
  loadingCharts?: boolean
  chartTimeframe?: '1W' | '1M' | '3M' | 'YTD' | 'ALL'
  onChartTimeframeChange?: (timeframe: '1W' | '1M' | '3M' | 'YTD' | 'ALL') => void
  viewMode?: 'table' | 'charts'
  onViewModeChange?: (mode: 'table' | 'charts') => void
  onDeleteRow?: (ticker: string) => Promise<void>
  watchlistName?: string
}

export default function ResultsWidget({
  data,
  searchQuery,
  onSearchChange,
  sortColumn,
  onSortChange,
  sortDirection,
  onSortDirectionChange,
  historicalData = {},
  loadingCharts = false,
  chartTimeframe = '1M',
  onChartTimeframeChange,
  viewMode: externalViewMode,
  onViewModeChange,
  onDeleteRow,
  watchlistName,
}: ResultsWidgetProps) {
  const [viewMode, setViewMode] = useState<'table' | 'charts'>(externalViewMode || 'table')
  const [selectedTickerForChart, setSelectedTickerForChart] = useState<string | null>(null)
  const [addingToWatchlist, setAddingToWatchlist] = useState<Set<string>>(new Set())
  const [deletingTicker, setDeletingTicker] = useState<string | null>(null)

  // Update internal viewMode when external viewMode changes
  useEffect(() => {
    if (externalViewMode) {
      setViewMode(externalViewMode)
    }
  }, [externalViewMode])

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

  // Notify parent when viewMode changes
  const handleViewModeChange = (newMode: 'table' | 'charts') => {
    setViewMode(newMode)
    onViewModeChange?.(newMode)
  }

  // Add ticker to global watchlist
  const handleAddToWatchlist = async (ticker: string) => {
    try {
      setAddingToWatchlist(prev => new Set([...prev, ticker]))
      await api.addToWatchlist('global', ticker)
      // Keep the loading state briefly for visual feedback
      setTimeout(() => {
        setAddingToWatchlist(prev => {
          const next = new Set(prev)
          next.delete(ticker)
          return next
        })
      }, 500)
    } catch (err) {
      console.error('Failed to add to watchlist:', err)
      setAddingToWatchlist(prev => {
        const next = new Set(prev)
        next.delete(ticker)
        return next
      })
    }
  }

  // Delete ticker from watchlist
  const handleDeleteTicker = async (ticker: string) => {
    if (!onDeleteRow) return
    try {
      setDeletingTicker(ticker)
      await onDeleteRow(ticker)
      setDeletingTicker(null)
    } catch (err) {
      console.error('Failed to delete ticker:', err)
      setDeletingTicker(null)
    }
  }

  // Filter data based on search query
  const filteredData = data.filter(row => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return Object.values(row).some(value =>
      String(value || '').toLowerCase().includes(query)
    )
  })

  // Sort filtered data
  const sortedData = [...filteredData].sort((a, b) => {
    if (!sortColumn) return 0

    const aVal = a[sortColumn]
    const bVal = b[sortColumn]

    // String comparison
    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortDirection === 'asc'
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal)
    }

    // Numeric comparison
    const aNum = typeof aVal === 'number' ? aVal : parseFloat(String(aVal || 0))
    const bNum = typeof bVal === 'number' ? bVal : parseFloat(String(bVal || 0))

    if (sortDirection === 'asc') {
      return aNum > bNum ? 1 : aNum < bNum ? -1 : 0
    } else {
      return bNum > aNum ? 1 : bNum < aNum ? -1 : 0
    }
  })

  // Get columns from first row - always put ticker and company_name first
  const getColumns = (): string[] => {
    if (data.length === 0) return []

    const allCols = Object.keys(data[0])
    const ticker = allCols.find(col => col.toLowerCase() === 'ticker')
    const companyName = allCols.find(col => col.toLowerCase() === 'company_name' || col.toLowerCase() === 'name')

    // Build ordered columns: ticker, company_name, then rest
    const orderedCols: string[] = []
    if (ticker) orderedCols.push(ticker)
    if (companyName) orderedCols.push(companyName)

    // Add remaining columns (excluding ticker and company_name)
    for (const col of allCols) {
      if (col !== ticker && col !== companyName) {
        orderedCols.push(col)
      }
    }

    return orderedCols
  }

  // Filter chart data by timeframe
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
        return data
    }

    return data.filter(point => {
      const pointDate = new Date(point.date)
      return pointDate >= cutoffDate
    })
  }

  const columns = getColumns()

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-800">
        <div className="flex items-center justify-between gap-4">
          {/* Results Title */}
          <h2 className="text-lg font-semibold text-white whitespace-nowrap">
            Results ({sortedData.length} of {data.length} matches)
          </h2>

          {/* Search Input */}
          <input
            type="text"
            placeholder="Search results..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-slate-600"
          />

          {/* Timeframe Selector - shown only in charts view */}
          {viewMode === 'charts' && onChartTimeframeChange && (
            <select
              value={chartTimeframe}
              onChange={(e) => onChartTimeframeChange(e.target.value as '1W' | '1M' | '3M' | 'YTD' | 'ALL')}
              className="px-4 py-1.5 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:border-slate-600 transition font-medium text-sm"
            >
              <option value="1W">1W</option>
              <option value="1M">1M</option>
              <option value="3M">3M</option>
              <option value="YTD">YTD</option>
              <option value="ALL">ALL</option>
            </select>
          )}

          {/* Table/Charts Toggle */}
          <div className="flex gap-2 bg-slate-800 border border-slate-700 rounded-lg p-1">
            <button
              onClick={() => handleViewModeChange('table')}
              className={`px-4 py-1.5 rounded transition font-medium text-sm whitespace-nowrap ${
                viewMode === 'table'
                  ? 'bg-purple-600 text-white'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
            >
              📊 Table
            </button>
            <button
              onClick={() => handleViewModeChange('charts')}
              className={`px-4 py-1.5 rounded transition font-medium text-sm whitespace-nowrap ${
                viewMode === 'charts'
                  ? 'bg-purple-600 text-white'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
            >
              📈 Charts
            </button>
          </div>
        </div>
      </div>

      {/* Table View */}
      {viewMode === 'table' && (
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-sm">
            <thead className="bg-slate-800/50 border-b border-slate-800 sticky top-0">
              <tr>
                {columns.map((col) => (
                  <th
                    key={col}
                    onClick={() => {
                      if (sortColumn === col) {
                        onSortDirectionChange(sortDirection === 'asc' ? 'desc' : 'asc')
                      } else {
                        onSortChange(col)
                        onSortDirectionChange('asc')
                      }
                    }}
                    className="px-6 py-3 text-left text-slate-300 font-medium cursor-pointer hover:bg-slate-700/50 transition"
                  >
                    <div className="flex items-center gap-2">
                      {col}
                      {sortColumn === col && (
                        <span className="text-xs text-slate-400">
                          {sortDirection === 'asc' ? '↑' : '↓'}
                        </span>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {sortedData.map((row, idx) => (
                <tr
                  key={idx}
                  onClick={() => setSelectedTickerForChart(row.ticker)}
                  className="hover:bg-slate-800/50 cursor-pointer transition"
                >
                  {columns.map((col) => {
                    const value = row[col]
                    let displayValue = String(value || '')

                    // Check if this is a date/timestamp column
                    const isDateColumn = col.toLowerCase().includes('date') || col.toLowerCase().includes('timestamp') || col.toLowerCase().includes('time')
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
                        if (col.toLowerCase().includes('volume') || col.toLowerCase().includes('vol')) {
                          displayValue = numValue.toFixed(0)
                        } else {
                          // Format other numbers with 3 decimal places
                          displayValue = numValue.toFixed(3)
                        }
                      }
                    }

                    return (
                      <td key={col} className="px-6 py-3 text-slate-300">
                        {displayValue}
                      </td>
                    )
                  })}
                  {/* Action Buttons */}
                  <td className="px-6 py-3 text-right space-x-2 flex justify-end">
                    {onDeleteRow ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteTicker(row.ticker)
                        }}
                        disabled={deletingTicker === row.ticker}
                        className={`px-3 py-1 rounded text-xs font-medium transition ${
                          deletingTicker === row.ticker
                            ? 'bg-red-600/50 text-red-200'
                            : 'bg-red-900/30 hover:bg-red-900/50 text-red-300'
                        }`}
                      >
                        {deletingTicker === row.ticker ? '⏳ Deleting...' : '🗑️ Delete'}
                      </button>
                    ) : (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleAddToWatchlist(row.ticker)
                        }}
                        disabled={addingToWatchlist.has(row.ticker)}
                        className={`px-3 py-1 rounded text-xs font-medium transition ${
                          addingToWatchlist.has(row.ticker)
                            ? 'bg-green-600/50 text-green-200'
                            : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                        }`}
                      >
                        {addingToWatchlist.has(row.ticker) ? '✓ Added' : '⭐ Watchlist'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Charts View */}
      {viewMode === 'charts' && (
        <div className="p-6 flex-1 overflow-auto">
          {sortedData.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              No matches in this result
            </div>
          ) : loadingCharts ? (
            <div className="text-center py-12 text-slate-400">
              Loading price history for {sortedData.length} tickers...
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sortedData.map((row: any) => {
                const ticker = row.ticker
                if (!ticker) return null

                const allData = historicalData[ticker] || []
                const chartData = filterDataByTimeframe(allData, chartTimeframe)

                // Calculate change percentage
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
                    onClick={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      console.log(`[ResultsWidget] Chart clicked: ${ticker}`)
                      setSelectedTickerForChart(ticker)
                    }}
                    className="bg-slate-800 rounded-lg overflow-hidden border border-slate-700 flex flex-col h-full cursor-pointer hover:border-slate-600 transition"
                  >
                    <div className="p-4 border-b border-slate-700 flex-shrink-0 bg-slate-900/50">
                      <div className="flex items-start justify-between gap-2">
                        {/* Left: Company name and ticker */}
                        <div className="flex-1 min-w-0">
                          {row.company_name && row.company_name !== ticker ? (
                            <>
                              <h3 className="text-lg font-bold text-white truncate">
                                {row.company_name}
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
                        <CardChart ticker={ticker} data={chartData} />
                      ) : (
                        <div className="flex items-center justify-center text-center text-slate-500">
                          <div>
                            <p className="text-xs">No data available</p>
                            <p className="text-xs mt-2 text-slate-600">{historicalData[ticker] ? 'Loading...' : 'Waiting for data'}</p>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Watchlist Button Footer */}
                    <div className="px-4 py-3 border-t border-slate-700 bg-slate-900/50 flex-shrink-0">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleAddToWatchlist(ticker)
                        }}
                        disabled={addingToWatchlist.has(ticker)}
                        className={`w-full px-3 py-2 rounded text-sm font-medium transition ${
                          addingToWatchlist.has(ticker)
                            ? 'bg-green-600/50 text-green-200'
                            : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                        }`}
                      >
                        {addingToWatchlist.has(ticker) ? '✓ Added to Watchlist' : '⭐ Add to Watchlist'}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Trading Chart Widget Modal - Click on chart to open */}
      {selectedTickerForChart && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setSelectedTickerForChart(null)}>
          <div className="bg-slate-950 border border-slate-800 rounded-lg w-full h-[90vh] max-w-7xl flex flex-col" onClick={(e) => e.stopPropagation()}>
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

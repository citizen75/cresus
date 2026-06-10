import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import ResultsWidget from '@/components/ResultsWidget'

export default function WatchlistPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [watchlistData, setWatchlistData] = useState<any[]>([])
  const [historicalData, setHistoricalData] = useState<{ [ticker: string]: any[] }>({})
  const [loadingData, setLoadingData] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortColumn, setSortColumn] = useState<string | null>('ticker')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')

  // Determine view mode from URL
  const isChartsView = location.pathname.includes('/charts')
  const [viewMode, setViewMode] = useState<'table' | 'charts'>(isChartsView ? 'charts' : 'table')
  const [chartTimeframe, setChartTimeframe] = useState<'1W' | '1M' | '3M' | 'YTD' | 'ALL'>('1M')

  useEffect(() => {
    // Load global watchlist on mount
    loadWatchlistData('global')
  }, [])

  useEffect(() => {
    // Load historical data when view mode changes to charts
    if (viewMode === 'charts' && watchlistData.length > 0) {
      loadHistoricalData()
    }
  }, [viewMode, watchlistData.length])

  const loadWatchlistData = async (watchlistName: string) => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.getWatchlist(watchlistName, 1000)

      // Use watchlist data directly (includes signal_score, OHLCV data)
      setWatchlistData(response.results || response.watchlist || [])
    } catch (err) {
      console.error('Failed to load watchlist data:', err)
      // Don't show error for empty watchlists, just show empty state
      setError(null)
      setWatchlistData([])
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteTicker = async (ticker: string) => {
    try {
      await api.removeFromWatchlist('global', ticker)
      // Refresh watchlist after deletion
      await loadWatchlistData('global')
    } catch (err) {
      console.error('Failed to delete ticker from watchlist:', err)
      throw err
    }
  }

  const loadHistoricalData = async () => {
    try {
      setLoadingData(true)
      const data: { [ticker: string]: any[] } = {}

      // Load historical data for each ticker
      for (const row of watchlistData) {
        const ticker = row.ticker
        if (!ticker) continue

        try {
          const history = await api.getHistoricalData(ticker, 365)
          if (history && history.data) {
            data[ticker] = history.data
          }
        } catch (err) {
          console.error(`Failed to load history for ${ticker}:`, err)
        }
      }

      setHistoricalData(data)
    } finally {
      setLoadingData(false)
    }
  }

  const handleViewModeChange = (mode: 'table' | 'charts') => {
    setViewMode(mode)
    // Update URL based on view mode
    if (mode === 'charts') {
      navigate('/watchlist/charts')
    } else {
      navigate('/watchlist')
    }
  }

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Global Watchlist</h1>
        <button
          onClick={() => loadWatchlistData('global')}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition"
        >
          ⟳ Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-800 rounded-lg p-4">
          <p className="text-red-300">{error}</p>
        </div>
      )}

      {loading || loadingData ? (
        <div className="text-center py-12 text-slate-400">Loading Global watchlist...</div>
      ) : (
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Global Watchlist - ResultsWidget */}
          <ResultsWidget
            data={watchlistData}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            sortColumn={sortColumn}
            onSortChange={setSortColumn}
            sortDirection={sortDirection}
            onSortDirectionChange={setSortDirection}
            viewMode={viewMode}
            onViewModeChange={handleViewModeChange}
            historicalData={historicalData}
            loadingCharts={loadingData}
            chartTimeframe={chartTimeframe}
            onChartTimeframeChange={setChartTimeframe}
            onDeleteRow={handleDeleteTicker}
            watchlistName="global"
          />
        </div>
      )}
    </div>
  )
}

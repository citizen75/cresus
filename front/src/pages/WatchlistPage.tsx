import { useState, useEffect } from 'react'
import { api } from '@/services/api'
import ResultsWidget from '@/components/ResultsWidget'

interface Watchlist {
  name: string
  tickers: string[]
  created_at?: string
  updated_at?: string
}

export default function WatchlistPage() {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedWatchlist, setSelectedWatchlist] = useState<string>('global')
  const [watchlistData, setWatchlistData] = useState<any[]>([])
  const [loadingData, setLoadingData] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortColumn, setSortColumn] = useState<string | null>('ticker')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const [viewMode, setViewMode] = useState<'table' | 'charts'>('table')

  useEffect(() => {
    fetchWatchlists()
  }, [])

  useEffect(() => {
    if (selectedWatchlist) {
      loadWatchlistData(selectedWatchlist)
    }
  }, [selectedWatchlist])

  const fetchWatchlists = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.listWatchlists()
      const lists = response.watchlists || []
      setWatchlists(lists)
      // Set global as default if it exists
      if (lists.some(w => w.name === 'global')) {
        setSelectedWatchlist('global')
      } else if (lists.length > 0) {
        setSelectedWatchlist(lists[0].name)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load watchlists')
    } finally {
      setLoading(false)
    }
  }

  const loadWatchlistData = async (watchlistName: string) => {
    try {
      setLoadingData(true)
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
      setLoadingData(false)
    }
  }

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Watchlists</h1>
        <button
          onClick={fetchWatchlists}
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

      {loading ? (
        <div className="text-center py-12 text-slate-400">Loading watchlists...</div>
      ) : watchlists.length === 0 ? (
        <div className="text-center py-12 text-slate-400">No watchlists found</div>
      ) : (
        <div className="flex gap-6 h-full overflow-hidden">
          {/* Watchlist Selector */}
          <div className="w-56 flex-shrink-0 bg-slate-800/50 rounded-lg border border-slate-700 overflow-auto">
            <div className="space-y-2 p-4">
              {watchlists.map((wl) => (
                <button
                  key={wl.name}
                  onClick={() => setSelectedWatchlist(wl.name)}
                  className={`w-full text-left px-4 py-3 rounded-lg transition ${
                    selectedWatchlist === wl.name
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  <div className="font-medium">{wl.name}</div>
                  <div className="text-xs text-slate-400 mt-1">{wl.tickers?.length || 0} tickers</div>
                </button>
              ))}
            </div>
          </div>

          {/* Results Widget */}
          {selectedWatchlist && !loadingData ? (
            <div className="flex-1 bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden flex flex-col">
              <ResultsWidget
                data={watchlistData}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                sortColumn={sortColumn}
                onSortChange={setSortColumn}
                sortDirection={sortDirection}
                onSortDirectionChange={setSortDirection}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
              />
            </div>
          ) : loadingData ? (
            <div className="flex-1 bg-slate-800/50 rounded-lg border border-slate-700 flex items-center justify-center">
              <p className="text-slate-400">Loading watchlist data...</p>
            </div>
          ) : (
            <div className="flex-1 bg-slate-800/50 rounded-lg border border-slate-700 flex items-center justify-center">
              <p className="text-slate-400">Select a watchlist</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

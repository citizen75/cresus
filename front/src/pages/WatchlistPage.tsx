import { useState, useEffect } from 'react'
import { api } from '@/services/api'

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
  const [selectedWatchlist, setSelectedWatchlist] = useState<string | null>(null)
  const [watchlistTickers, setWatchlistTickers] = useState<string[]>([])
  const [removingTicker, setRemovingTicker] = useState<Set<string>>(new Set())

  useEffect(() => {
    fetchWatchlists()
  }, [])

  useEffect(() => {
    if (selectedWatchlist) {
      loadWatchlistTickers(selectedWatchlist)
    }
  }, [selectedWatchlist])

  const fetchWatchlists = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.listWatchlists()
      setWatchlists(response.watchlists || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load watchlists')
    } finally {
      setLoading(false)
    }
  }

  const loadWatchlistTickers = async (watchlistName: string) => {
    try {
      const response = await api.getWatchlistTickers(watchlistName)
      setWatchlistTickers(response.tickers || [])
    } catch (err) {
      console.error('Failed to load watchlist tickers:', err)
    }
  }

  const handleRemoveTicker = async (ticker: string) => {
    if (!selectedWatchlist) return

    try {
      setRemovingTicker(prev => new Set([...prev, ticker]))
      await api.removeFromWatchlist(selectedWatchlist, ticker)
      setWatchlistTickers(prev => prev.filter(t => t !== ticker))
    } catch (err) {
      console.error('Failed to remove ticker:', err)
      setError('Failed to remove ticker from watchlist')
    } finally {
      setRemovingTicker(prev => {
        const next = new Set(prev)
        next.delete(ticker)
        return next
      })
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
        <div className="flex gap-6 h-full">
          {/* Watchlist List */}
          <div className="w-64 flex-shrink-0 bg-slate-800/50 rounded-lg border border-slate-700 overflow-auto">
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

          {/* Watchlist Details */}
          {selectedWatchlist ? (
            <div className="flex-1 bg-slate-800/50 rounded-lg border border-slate-700 overflow-auto">
              <div className="p-6">
                <h2 className="text-xl font-bold text-white mb-6">{selectedWatchlist}</h2>

                {watchlistTickers.length === 0 ? (
                  <p className="text-slate-400 text-center py-8">No tickers in this watchlist</p>
                ) : (
                  <div className="space-y-2">
                    {watchlistTickers.map((ticker) => (
                      <div
                        key={ticker}
                        className="flex items-center justify-between bg-slate-700/50 p-4 rounded-lg border border-slate-600 hover:border-slate-500 transition"
                      >
                        <div className="text-white font-medium">{ticker}</div>
                        <button
                          onClick={() => handleRemoveTicker(ticker)}
                          disabled={removingTicker.has(ticker)}
                          className="px-3 py-1 bg-red-600/50 hover:bg-red-600 text-red-200 rounded text-sm transition disabled:opacity-50"
                        >
                          {removingTicker.has(ticker) ? 'Removing...' : 'Remove'}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 bg-slate-800/50 rounded-lg border border-slate-700 flex items-center justify-center">
              <p className="text-slate-400">Select a watchlist to view tickers</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

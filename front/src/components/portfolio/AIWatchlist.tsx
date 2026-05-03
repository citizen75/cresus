import { useState, useEffect } from 'react'

interface AIWatchlistProps {
  name: string
}

interface WatchlistItem {
  rank: number
  stock: string
  ticker: string
  aiScore: number
  match: string
  updatePotential: string
  riskScore: string
  drivers: string
}

export default function AIWatchlist({ name }: AIWatchlistProps) {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sector, setSector] = useState('All sectors')
  const [country, setCountry] = useState('All countries')
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState('AI Score')
  const [currentPage, setCurrentPage] = useState(1)

  // Load watchlist from API
  useEffect(() => {
    const loadWatchlist = async () => {
      try {
        setLoading(true)
        // Use portfolio name as strategy name (e.g., "Momentum cac" -> "momentum_cac")
        const strategyName = name.toLowerCase().replace(/\s+/g, '_')
        const response = await fetch(`http://localhost:8000/api/v1/watchlists/${strategyName}`)

        if (!response.ok) {
          throw new Error('Failed to load watchlist')
        }

        const data = await response.json()

        // Transform API data to table format
        const transformedWatchlist: WatchlistItem[] = data.watchlist.map((item: any, index: number) => ({
          rank: index + 1,
          stock: item.ticker.replace('.PA', '').toUpperCase(),
          ticker: item.ticker,
          aiScore: Math.round((item.signal_score || 0) * 100),
          match: item.signal_score >= 0.8 ? 'Excellent' : item.signal_score >= 0.6 ? 'Very Good' : 'Good',
          updatePotential: `${Math.round((item.close || 0) / 100)}%`,
          riskScore: 'Medium',
          drivers: (item.signals || '').split(',').filter(Boolean).join(', ') || 'Strategy match'
        }))

        setWatchlist(transformedWatchlist)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load watchlist')
        setWatchlist([])
      } finally {
        setLoading(false)
      }
    }

    loadWatchlist()
  }, [name])

  const filtered = watchlist.filter(item =>
    item.stock.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.ticker.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const itemsPerPage = 8
  const totalPages = Math.ceil(filtered.length / itemsPerPage)
  const paginatedItems = filtered.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-slate-400">Loading watchlist...</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-red-400">Error: {error}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">AI Stock Watchlist</h2>
          <p className="text-slate-400 text-sm mt-1">Cresus AI-selected stocks ranked by relevance to your strategy</p>
        </div>
        <button
          onClick={() => window.location.reload()}
          className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition">
          Refresh ranks
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <select
          value={sector}
          onChange={(e) => setSector(e.target.value)}
          className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:border-slate-600 transition"
        >
          <option>All sectors</option>
          <option>Technology</option>
          <option>Finance</option>
          <option>Healthcare</option>
        </select>

        <select
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:border-slate-600 transition"
        >
          <option>All countries</option>
          <option>United States</option>
          <option>Canada</option>
          <option>Europe</option>
        </select>

        <div className="flex-1 relative">
          <input
            type="text"
            placeholder="Search stocks"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              setCurrentPage(1)
            }}
            className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg focus:outline-none focus:border-purple-600"
          />
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500">🔍</span>
        </div>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:border-slate-600 transition"
        >
          <option>AI Score</option>
          <option>Match Score</option>
          <option>Update Potential</option>
          <option>Risk Score</option>
        </select>

        <button className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 transition flex items-center gap-2">
          <span>⚙️</span> Filters
        </button>
      </div>

      {/* Watchlist Table */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-800/50 border-b border-slate-800">
              <tr>
                <th className="px-6 py-4 text-left text-slate-400 font-medium">Rank</th>
                <th className="px-6 py-4 text-left text-slate-400 font-medium">Stock</th>
                <th className="px-6 py-4 text-left text-slate-400 font-medium">AI Score</th>
                <th className="px-6 py-4 text-left text-slate-400 font-medium">Match to strategy</th>
                <th className="px-6 py-4 text-left text-slate-400 font-medium">Update potential</th>
                <th className="px-6 py-4 text-left text-slate-400 font-medium">Risk score</th>
                <th className="px-6 py-4 text-left text-slate-400 font-medium">Key drivers</th>
              </tr>
            </thead>
            <tbody>
              {paginatedItems.map((item) => (
                <tr key={item.ticker} className="border-t border-slate-800 hover:bg-slate-800/30 transition">
                  <td className="px-6 py-4 text-white font-medium">{item.rank}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-slate-700 rounded flex items-center justify-center text-xs font-bold text-white">
                        {item.ticker.charAt(0)}
                      </div>
                      <div>
                        <p className="text-white font-medium">{item.stock}</p>
                        <p className="text-slate-400 text-xs">{item.ticker}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-slate-700 rounded-full h-2">
                        <div
                          className="bg-gradient-to-r from-purple-600 to-purple-500 h-2 rounded-full"
                          style={{ width: `${item.aiScore}%` }}
                        ></div>
                      </div>
                      <span className="text-white font-medium text-sm">{item.aiScore}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-3 py-1 rounded text-xs font-medium ${
                      item.match === 'Excellent' ? 'bg-green-900/30 text-green-400' :
                      item.match === 'Very Good' ? 'bg-blue-900/30 text-blue-400' :
                      'bg-slate-800/30 text-slate-400'
                    }`}>
                      {item.match}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-green-400 font-medium">{item.updatePotential}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-3 py-1 rounded text-xs font-medium ${
                      item.riskScore === 'High' ? 'bg-red-900/30 text-red-400' :
                      'bg-yellow-900/30 text-yellow-400'
                    }`}>
                      {item.riskScore}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-400 text-xs max-w-xs">{item.drivers}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-900 flex items-center justify-between">
          <p className="text-slate-400 text-sm">Showing 1-{Math.min(itemsPerPage, filtered.length)} of {filtered.length}</p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 bg-slate-800 border border-slate-700 text-slate-300 rounded hover:bg-slate-700 disabled:opacity-50 transition"
            >
              ←
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
                className={`px-3 py-1 rounded transition ${
                  page === currentPage
                    ? 'bg-purple-600 text-white'
                    : 'bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700'
                }`}
              >
                {page}
              </button>
            ))}
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 bg-slate-800 border border-slate-700 text-slate-300 rounded hover:bg-slate-700 disabled:opacity-50 transition"
            >
              →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

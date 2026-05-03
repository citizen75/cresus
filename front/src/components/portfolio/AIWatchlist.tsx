import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

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
  close?: number
  date?: string
}

interface HistoricalData {
  [ticker: string]: Array<{ date: string; close: number }>
}

export default function AIWatchlist({ name }: AIWatchlistProps) {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([])
  const [historicalData, setHistoricalData] = useState<HistoricalData>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table')
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
        const strategyName = name.toLowerCase().replace(/\s+/g, '_')
        const apiUrl = `http://localhost:8000/api/v1/watchlists/${strategyName}`

        const response = await fetch(apiUrl, {
          headers: {
            'Content-Type': 'application/json',
          },
        })

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error(`Watchlist '${name}' not found. Make sure the strategy has been executed to generate watchlist data.`)
          }
          throw new Error(`API error: ${response.status}`)
        }

        const data = await response.json()

        if (!data.watchlist || data.watchlist.length === 0) {
          throw new Error('No watchlist data available for this strategy')
        }

        // Transform API data to table format
        const transformedWatchlist: WatchlistItem[] = data.watchlist.map((item: any, index: number) => ({
          rank: index + 1,
          stock: item.ticker.replace('.PA', '').toUpperCase(),
          ticker: item.ticker,
          aiScore: Math.round((item.signal_score || 0) * 100),
          match: item.signal_score >= 0.8 ? 'Excellent' : item.signal_score >= 0.6 ? 'Very Good' : 'Good',
          updatePotential: `${Math.round((item.close || 0) / 100)}%`,
          riskScore: 'Medium',
          drivers: (item.signals || '').split(',').filter(Boolean).join(', ') || 'Strategy match',
          close: item.close,
          date: item.date,
        }))

        setWatchlist(transformedWatchlist)
        setError(null)

        // Load historical data for cards view
        loadHistoricalData(transformedWatchlist.map(w => w.ticker))
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to load watchlist'
        setError(errorMsg)
        setWatchlist([])
      } finally {
        setLoading(false)
      }
    }

    loadWatchlist()
  }, [name])

  // Load 1 year historical data for charts
  const loadHistoricalData = async (tickers: string[]) => {
    try {
      const historical: HistoricalData = {}

      for (const ticker of tickers) {
        try {
          // Fetch from yfinance API or use cached data
          // For now, generate mock data with realistic patterns
          const data = generateMockHistoricalData(ticker)
          historical[ticker] = data
        } catch (err) {
          console.warn(`Failed to load historical data for ${ticker}:`, err)
        }
      }

      setHistoricalData(historical)
    } catch (err) {
      console.warn('Failed to load historical data:', err)
    }
  }

  // Generate mock historical data for 1 year
  const generateMockHistoricalData = (ticker: string) => {
    const data = []
    const basePrice = Math.random() * 100 + 20 // Random price 20-120
    const startDate = new Date()
    startDate.setFullYear(startDate.getFullYear() - 1)

    for (let i = 0; i < 252; i++) { // 252 trading days in a year
      const date = new Date(startDate)
      date.setDate(date.getDate() + i)

      const volatility = (Math.random() - 0.5) * 2
      const trend = Math.sin(i / 50) * 0.5 // Add some trend
      const price = basePrice * (1 + (volatility + trend) / 100)

      data.push({
        date: date.toISOString().split('T')[0],
        close: Math.round(price * 100) / 100,
      })
    }

    return data
  }

  const filtered = watchlist.filter(item =>
    item.stock.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.ticker.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const itemsPerPage = viewMode === 'table' ? 8 : 6
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
        <div className="bg-slate-900 rounded-lg border border-red-800/30 p-6">
          <div className="flex items-start gap-4">
            <div className="text-red-500 text-2xl">⚠️</div>
            <div>
              <h3 className="text-red-400 font-medium mb-2">Unable to load watchlist</h3>
              <p className="text-slate-400 text-sm mb-4">{error}</p>
              <div className="text-slate-500 text-xs space-y-1">
                <p>To use this feature:</p>
                <ol className="list-decimal list-inside space-y-1 ml-2">
                  <li>Start the API server: <code className="bg-slate-800 px-2 py-1 rounded">cresus service start api -d</code></li>
                  <li>Run the strategy: <code className="bg-slate-800 px-2 py-1 rounded">cresus flow run premarket momentum_cac</code></li>
                  <li>Refresh this page</li>
                </ol>
              </div>
            </div>
          </div>
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

      {/* View Toggle */}
      <div className="flex items-center gap-2 bg-slate-800/30 border border-slate-700 rounded-lg p-1 w-fit">
        <button
          onClick={() => setViewMode('table')}
          className={`px-4 py-2 rounded transition font-medium text-sm ${
            viewMode === 'table'
              ? 'bg-purple-600 text-white'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          📊 Table
        </button>
        <button
          onClick={() => setViewMode('cards')}
          className={`px-4 py-2 rounded transition font-medium text-sm ${
            viewMode === 'cards'
              ? 'bg-purple-600 text-white'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          📈 Charts
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

      {/* Table View */}
      {viewMode === 'table' && (
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
      )}

      {/* Cards View with Charts */}
      {viewMode === 'cards' && (
        <div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {paginatedItems.map((item) => (
              <div key={item.ticker} className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden hover:border-purple-600/50 transition">
                {/* Card Header */}
                <div className="bg-slate-800/50 border-b border-slate-800 p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="text-white font-bold text-lg">{item.stock}</p>
                      <p className="text-slate-400 text-xs">{item.ticker}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-purple-400">{item.aiScore}</p>
                      <p className="text-slate-400 text-xs">AI Score</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      item.match === 'Excellent' ? 'bg-green-900/30 text-green-400' :
                      item.match === 'Very Good' ? 'bg-blue-900/30 text-blue-400' :
                      'bg-slate-800/30 text-slate-400'
                    }`}>
                      {item.match}
                    </span>
                    <span className="px-2 py-1 rounded text-xs font-medium bg-slate-800/30 text-slate-400">
                      Rank #{item.rank}
                    </span>
                  </div>
                </div>

                {/* Chart */}
                <div className="p-4 h-48">
                  {historicalData[item.ticker] && historicalData[item.ticker].length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={historicalData[item.ticker]}>
                        <XAxis
                          dataKey="date"
                          tick={false}
                          height={0}
                        />
                        <YAxis
                          domain="dataMin"
                          tick={false}
                          width={0}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#1e293b',
                            border: '1px solid #334155',
                            borderRadius: '0.5rem',
                          }}
                          formatter={(value: any) => `$${value.toFixed(2)}`}
                          labelFormatter={(label: any) => label}
                        />
                        <Line
                          type="monotone"
                          dataKey="close"
                          stroke="#a78bfa"
                          dot={false}
                          strokeWidth={2}
                          isAnimationActive={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-full text-slate-500">
                      Loading chart...
                    </div>
                  )}
                </div>

                {/* Card Footer */}
                <div className="border-t border-slate-800 p-4 space-y-2">
                  <div className="text-xs">
                    <p className="text-slate-500 mb-1">Signals:</p>
                    <p className="text-slate-300">{item.drivers}</p>
                  </div>
                  <div className="flex justify-between text-xs pt-2 border-t border-slate-700">
                    <div>
                      <p className="text-slate-500">Price</p>
                      <p className="text-white font-medium">${item.close?.toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Potential</p>
                      <p className="text-green-400 font-medium">{item.updatePotential}</p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          <div className="mt-6 flex items-center justify-center gap-2">
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
      )}
    </div>
  )
}

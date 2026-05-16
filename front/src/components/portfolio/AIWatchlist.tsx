import { useState, useEffect } from 'react'
import CardChart from '@/components/CardChart'
import TradingChart from '@/components/TradingChart'
import Spinner from '@/components/Spinner'
import { getApiBaseUrl } from '@/services/api'

// Ticker to company name mapping
const COMPANY_NAMES: { [key: string]: string } = {
  'STMPA.PA': 'STMicroelectronics',
  'TTE.PA': 'TotalEnergies',
  'PUB.PA': 'Publicis Groupe',
  'DSY.PA': 'Dassault Systèmes',
  'SGO.PA': 'Sanofi',
  'VIE.PA': 'Veolia',
  'EDEN.PA': 'EdenWorks',
  'LR.PA': 'Legrand',
  'AC.PA': 'Accor',
  'AI.PA': 'Air Liquide',
  'AIR.PA': 'Airbus',
  'MT.AS': 'ArcelorMittal',
  'CS.PA': 'Crédit Suisse',
  'BNP.PA': 'BNP Paribas',
  'EN.PA': 'Engie',
  'CAP.PA': 'Capgemini',
  'CA.PA': 'Carrefour',
  'ACA.PA': 'Acacia Research',
  'BN.PA': 'Bouygues',
  'ENGI.PA': 'Engie',
  'EL.PA': 'EssiloLuxottica',
  'ERF.PA': 'Eramet',
  'RMS.PA': 'Remy Cointreau',
  'KER.PA': 'Kering',
  'OR.PA': 'L\'Oréal',
  'MC.PA': 'LVMH',
  'ML.PA': 'Michelin',
  'ORA.PA': 'Orange',
  'RI.PA': 'Pernod Ricard',
  'RNO.PA': 'Renault',
  'SAF.PA': 'Safran',
  'SAN.PA': 'Sanofi',
  'SU.PA': 'Schneider Electric',
  'GLE.PA': 'Société Générale',
  'STLAP.PA': 'Stellantis',
  'TEP.PA': 'TotalEnergies',
  'HO.PA': 'Thales',
  'DG.PA': 'Vinci',
  'VIV.PA': 'Vivendi',
}

interface AIWatchlistProps {
  name: string
}

interface WatchlistItem {
  rank: number
  stock: string
  companyName?: string
  ticker: string
  aiScore: number
  match: string
  updatePotential: string
  riskScore: string
  drivers: string
  close?: number
  date?: string
  currentPrice?: number
  previousClose?: number
  priceChange?: number
  targetPrice?: number
  analystRating?: string
  analystCount?: number
  upsidePotential?: number
}

interface HistoricalData {
  [ticker: string]: Array<{ date: string; close: number; ema_20?: number; ema_50?: number }>
}

export default function AIWatchlist({ name }: AIWatchlistProps) {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([])
  const [historicalData, setHistoricalData] = useState<HistoricalData>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('cards')
  const [sector, setSector] = useState('All sectors')
  const [country, setCountry] = useState('All countries')
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState('AI Score')
  const [currentPage, setCurrentPage] = useState(1)
  const [period, setPeriod] = useState('1Y')
  const [chartTicker, setChartTicker] = useState<string | null>(null)

  // Reload historical data when period changes
  useEffect(() => {
    if (watchlist.length > 0) {
      loadHistoricalData(watchlist.map(w => w.ticker), period)
    }
  }, [period])

  // Load watchlist from API
  useEffect(() => {
    const loadWatchlist = async () => {
      try {
        setLoading(true)
        const baseUrl = getApiBaseUrl()
        const apiUrl = `${baseUrl}/api/v1/backtests/strategy/${name}/watchlist`

        const response = await fetch(apiUrl, {
          headers: {
            'Content-Type': 'application/json',
          },
        })

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error(`Watchlist '${name}' not found. Make sure you've run the strategy in live mode to generate watchlist data.`)
          }
          throw new Error(`API error: ${response.status}`)
        }

        const data = await response.json()

        if (!data.data?.watchlist || data.data.watchlist.length === 0) {
          throw new Error('No watchlist data available for this strategy')
        }

        // Transform API data to table format
        const transformedWatchlist: WatchlistItem[] = data.data.watchlist.map((item: any, index: number) => ({
          rank: index + 1,
          stock: item.ticker.replace('.PA', '').toUpperCase(),
          companyName: COMPANY_NAMES[item.ticker],
          ticker: item.ticker,
          aiScore: Math.round(item.composite_score || 0),
          match: (item.composite_score || 0) >= 80 ? 'Excellent' : (item.composite_score || 0) >= 65 ? 'Very Good' : 'Good',
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

  // Fetch real-time prices and company names for each ticker
  useEffect(() => {
    if (watchlist.length === 0) return

    const loadFundamentalData = async () => {
      const updatedWatchlist = [...watchlist]
      const baseUrl = getApiBaseUrl()

      for (let i = 0; i < updatedWatchlist.length; i++) {
        try {
          const response = await fetch(
            `${baseUrl}/api/v1/data/fundamental/${updatedWatchlist[i].ticker}`
          )
          if (response.ok) {
            const data = await response.json()
            const currentPrice = data.data?.quotation?.current_price
            const previousClose = data.data?.quotation?.previous_close
            const companyName = data.data?.company?.name
            const analysts = data.data?.analysts

            if (currentPrice) {
              updatedWatchlist[i].currentPrice = currentPrice
              updatedWatchlist[i].previousClose = previousClose

              // Calculate price change from previous close
              if (previousClose) {
                const change = ((currentPrice - previousClose) / previousClose) * 100
                updatedWatchlist[i].priceChange = change
              }
            }
            if (companyName) {
              updatedWatchlist[i].companyName = companyName
            }
            if (analysts) {
              updatedWatchlist[i].targetPrice = analysts.target_price
              updatedWatchlist[i].analystRating = analysts.recommendation
              updatedWatchlist[i].analystCount = analysts.analyst_count
              updatedWatchlist[i].upsidePotential = analysts.upside_potential
            }
          }
        } catch (err) {
          console.warn(`Failed to load fundamental data for ${updatedWatchlist[i].ticker}:`, err)
        }
      }

      setWatchlist(updatedWatchlist)
    }

    loadFundamentalData()
  }, [watchlist.length])

  // Load historical data for charts
  const loadHistoricalData = async (tickers: string[], selectedPeriod: string = '1Y') => {
    try {
      const baseUrl = getApiBaseUrl()
      const historical: HistoricalData = {}

      // Map period to days
      const daysMap: { [key: string]: number } = {
        '1W': 7,
        '1M': 30,
        '3M': 90,
        '6M': 180,
        'YTD': 365,
        '1Y': 365,
        'All': 1000,
      }
      const days = daysMap[selectedPeriod] || 365

      for (const ticker of tickers) {
        try {
          const response = await fetch(
            `${baseUrl}/api/v1/data/history/${ticker}?days=${days}`
          )

          if (response.ok) {
            const data = await response.json()
            if (data.data && data.data.length > 0) {
              historical[ticker] = data.data.map((item: any) => ({
                date: item.date || new Date(item.timestamp).toISOString().split('T')[0],
                close: item.close,
                ema_20: item.ema_20,
                ema_50: item.ema_50,
              }))
            }
          }
        } catch (err) {
          console.warn(`Failed to load historical data for ${ticker}:`, err)
        }
      }

      setHistoricalData(historical)
    } catch (err) {
      console.warn('Failed to load historical data:', err)
    }
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
      <div className="flex items-center gap-4">
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

        {/* Period Selection (only in charts view) */}
        {viewMode === 'cards' && (
          <div className="flex items-center gap-2 bg-slate-800/30 border border-slate-700 rounded-lg p-1">
            {['1W', '1M', '3M', '6M', 'YTD', '1Y', 'All'].map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-2 rounded transition font-medium text-xs ${
                  period === p
                    ? 'bg-purple-600 text-white'
                    : 'text-slate-400 hover:text-slate-300'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        )}
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
                  <th className="px-6 py-4 text-left text-slate-400 font-medium">Current Price</th>
                  <th className="px-6 py-4 text-left text-slate-400 font-medium">Target</th>
                  <th className="px-6 py-4 text-left text-slate-400 font-medium">Analyst Rating</th>
                  <th className="px-6 py-4 text-left text-slate-400 font-medium">Key drivers</th>
                  <th className="px-6 py-4 text-center text-slate-400 font-medium">Chart</th>
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
                          <p className="text-white font-medium">{item.companyName || item.stock}</p>
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
                      <div className="flex flex-col">
                        <span className="text-white font-medium">
                          {item.currentPrice ? `€${item.currentPrice.toFixed(2)}` : '—'}
                        </span>
                        {item.priceChange !== undefined && (
                          <span className={`text-xs font-medium ${
                            item.priceChange >= 0 ? 'text-green-400' : 'text-red-400'
                          }`}>
                            {item.priceChange >= 0 ? '+' : ''}{item.priceChange.toFixed(2)}%
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {item.targetPrice ? (
                        <div className="flex flex-col">
                          <span className="text-white font-medium">€{item.targetPrice.toFixed(2)}</span>
                          {item.upsidePotential && (
                            <span className={`text-xs font-medium ${
                              item.upsidePotential > 0 ? 'text-green-400' : 'text-red-400'
                            }`}>
                              {item.upsidePotential > 0 ? '+' : ''}{item.upsidePotential.toFixed(2)}%
                            </span>
                          )}
                        </div>
                      ) : '—'}
                    </td>
                    <td className="px-6 py-4">
                      {item.analystRating ? (
                        <div className="flex flex-col">
                          <span className={`px-3 py-1 rounded text-xs font-medium w-fit ${
                            item.analystRating.includes('Buy') ? 'bg-green-900/30 text-green-400' :
                            item.analystRating.includes('Sell') ? 'bg-red-900/30 text-red-400' :
                            'bg-yellow-900/30 text-yellow-400'
                          }`}>
                            {item.analystRating}
                          </span>
                          {item.analystCount && (
                            <span className="text-slate-400 text-xs mt-1">{item.analystCount} analysts</span>
                          )}
                        </div>
                      ) : '—'}
                    </td>
                    <td className="px-6 py-4 text-slate-400 text-xs max-w-xs">{item.drivers}</td>
                    <td className="px-6 py-4 text-center">
                      <button
                        onClick={() => setChartTicker(item.ticker)}
                        className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded transition text-sm font-medium"
                        title="View chart"
                      >
                        📈
                      </button>
                    </td>
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
                      <p className="text-white font-bold text-lg">{item.companyName || item.stock}</p>
                      <p className="text-slate-400 text-xs">{item.ticker}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-purple-400">{item.aiScore}</p>
                      <p className="text-slate-400 text-xs">AI Score</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex gap-2 items-center flex-wrap">
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
                      <div className="flex gap-1 flex-wrap">
                        {item.drivers.split(',').map((driver, idx) => (
                          <span key={idx} className="px-2 py-1 rounded text-xs font-medium bg-purple-900/30 text-purple-300">
                            {driver.trim()}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Chart */}
                {historicalData[item.ticker] && historicalData[item.ticker].length > 0 ? (
                  <CardChart
                    data={historicalData[item.ticker]}
                    ticker={item.ticker}
                    showVariation={false}
                  />
                ) : (
                  <div className="p-4 h-48 bg-slate-800/20 flex items-center justify-center">
                    <Spinner />
                  </div>
                )}

                {/* Price Range Row - First/Var/Last */}
                {historicalData[item.ticker] && historicalData[item.ticker].length > 0 && (() => {
                  const data = historicalData[item.ticker]
                  const firstPrice = data[0]?.close
                  const lastPrice = data[data.length - 1]?.close
                  const change = firstPrice ? ((lastPrice - firstPrice) / firstPrice) * 100 : 0
                  return (
                    <div className="border-t border-slate-800 px-4 py-3 bg-slate-800/30">
                      <div className="flex justify-between items-center text-xs">
                        <div className="flex flex-col items-center flex-1">
                          <p className="text-slate-500 text-xs mb-1">First</p>
                          <p className="text-white font-medium">€{firstPrice?.toFixed(2)}</p>
                        </div>
                        <div className="flex flex-col items-center flex-1">
                          <p className="text-slate-500 text-xs mb-1">Var</p>
                          <p className={`font-medium ${change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {change >= 0 ? '↗' : '↘'} {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                          </p>
                        </div>
                        <div className="flex flex-col items-center flex-1">
                          <p className="text-slate-500 text-xs mb-1">Last</p>
                          <p className="text-white font-medium">€{lastPrice?.toFixed(2)}</p>
                        </div>
                      </div>
                    </div>
                  )
                })()}

                {/* Card Footer */}
                <div className="border-t border-slate-800 p-4 space-y-2">

                  {/* Analyst Targets */}
                  {item.targetPrice && (
                    <div className="border-t border-slate-700 pt-2">
                      <p className="text-slate-500 mb-2">Analyst Targets</p>
                      <div className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-400">Target Price</span>
                          <span className="text-white font-medium">€{item.targetPrice.toFixed(2)}</span>
                        </div>
                        {item.upsidePotential && (
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-400">Upside</span>
                            <span className={`font-medium ${item.upsidePotential > 0 ? 'text-green-400' : 'text-red-400'}`}>
                              {item.upsidePotential.toFixed(2)}%
                            </span>
                          </div>
                        )}
                        {item.analystRating && (
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-400">Rating</span>
                            <span className={`font-medium px-2 py-0.5 rounded ${
                              item.analystRating.includes('Buy') ? 'bg-green-900/30 text-green-400' :
                              item.analystRating.includes('Sell') ? 'bg-red-900/30 text-red-400' :
                              'bg-yellow-900/30 text-yellow-400'
                            }`}>
                              {item.analystRating}
                            </span>
                          </div>
                        )}
                        {item.analystCount > 0 && (
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-400">Analysts</span>
                            <span className="text-white">{item.analystCount}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="flex gap-2 mt-4 pt-4 border-t border-slate-700">
                    <button
                      onClick={() => setChartTicker(item.ticker)}
                      className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm font-medium transition"
                    >
                      📈 View Chart
                    </button>
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

      {/* Chart Modal */}
      {chartTicker && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-lg border border-slate-800 w-full max-w-6xl h-screen max-h-[90vh] flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 p-6">
              <h3 className="text-xl font-bold text-white">
                {watchlist.find(w => w.ticker === chartTicker)?.companyName || chartTicker} Chart
              </h3>
              <button
                onClick={() => setChartTicker(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition"
              >
                ✕
              </button>
            </div>

            {/* Chart Container */}
            <div className="flex-1 overflow-auto">
              <TradingChart ticker={chartTicker} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

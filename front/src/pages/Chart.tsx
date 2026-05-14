import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import TradingChart from '@/components/TradingChart'
import { api } from '@/services/api'

interface Portfolio {
  name: string
}

interface Holding {
  ticker: string
  quantity: number
  avg_entry_price: number
  current_price: number
  position_value: number
  position_gain: number
  position_gain_pct: number
}

export default function ChartPage() {
  const { ticker: urlTicker } = useParams<{ ticker?: string }>()
  const navigate = useNavigate()
  const [selectedTicker, setSelectedTicker] = useState(urlTicker || '^FCHI')
  const [timeframe, setTimeframe] = useState('1D')
  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [selectedPortfolio, setSelectedPortfolio] = useState<string>('')
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [watchlist, setWatchlist] = useState<any[]>([])
  const [loadingPortfolios, setLoadingPortfolios] = useState(true)
  const [loadingHoldings, setLoadingHoldings] = useState(false)
  const [loadingWatchlist, setLoadingWatchlist] = useState(false)
  const [activeTab, setActiveTab] = useState<'holdings' | 'watchlist'>('holdings')
  const [sortBy, setSortBy] = useState<'ticker' | 'price' | 'score' | 'entry'>('score')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [selectedIndicators, setSelectedIndicators] = useState<Set<string>>(new Set(['RSI 14', 'MACD']))
  const [visibleWindow, setVisibleWindow] = useState<'1M' | '3M' | '6M' | 'YTD' | '1Y' | '2Y'>('1Y')

  // Handle column sort
  const handleSort = (column: 'ticker' | 'price' | 'score' | 'entry') => {
    if (sortBy === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortDirection('desc')
    }
  }

  // Handle indicator toggle
  const toggleIndicator = (indicator: string) => {
    const newIndicators = new Set(selectedIndicators)
    if (newIndicators.has(indicator)) {
      newIndicators.delete(indicator)
    } else {
      newIndicators.add(indicator)
    }
    setSelectedIndicators(newIndicators)
  }

  // Get sorted watchlist
  const sortedWatchlist = [...watchlist].sort((a, b) => {
    let aVal: any
    let bVal: any

    switch (sortBy) {
      case 'ticker':
        aVal = a.ticker.toLowerCase()
        bVal = b.ticker.toLowerCase()
        break
      case 'price':
        aVal = parseFloat(a.close) || 0
        bVal = parseFloat(b.close) || 0
        break
      case 'score':
        aVal = parseFloat(a.signal_score) || 0
        bVal = parseFloat(b.signal_score) || 0
        break
      case 'entry':
        aVal = a.entry_score || 0
        bVal = b.entry_score || 0
        break
      default:
        return 0
    }

    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1
    return 0
  })

  // Update selectedTicker when URL ticker parameter changes
  useEffect(() => {
    if (urlTicker) {
      setSelectedTicker(urlTicker)
    }
  }, [urlTicker])

  // Load portfolios on mount
  useEffect(() => {
    const loadPortfolios = async () => {
      try {
        const result = await api.listPortfolios()
        const portfolioList = result.portfolios || []
        setPortfolios(portfolioList)
        if (portfolioList.length > 0) {
          setSelectedPortfolio(portfolioList[0].name)
        }
      } catch (err) {
        console.error('Failed to load portfolios:', err)
      } finally {
        setLoadingPortfolios(false)
      }
    }

    loadPortfolios()
  }, [])

  // Load holdings when portfolio changes
  useEffect(() => {
    if (!selectedPortfolio) return

    const loadHoldings = async () => {
      setLoadingHoldings(true)
      try {
        const result = await api.getPortfolioDetails(selectedPortfolio)
        setHoldings(result.positions || [])
        if (result.positions && result.positions.length > 0) {
          setSelectedTicker(result.positions[0].ticker)
        }
      } catch (err) {
        console.error('Failed to load holdings:', err)
        setHoldings([])
      } finally {
        setLoadingHoldings(false)
      }
    }

    loadHoldings()
  }, [selectedPortfolio])

  // Load watchlist when tab changes to watchlist
  useEffect(() => {
    if (activeTab !== 'watchlist' || !selectedPortfolio) return

    const loadWatchlist = async () => {
      setLoadingWatchlist(true)
      try {
        const result = await api.getPortfolioWatchlist(selectedPortfolio)
        setWatchlist(result.watchlist || [])
        if (result.watchlist && result.watchlist.length > 0) {
          setSelectedTicker(result.watchlist[0].symbol || result.watchlist[0].ticker)
        }
      } catch (err) {
        console.error('Failed to load watchlist:', err)
        setWatchlist([])
      } finally {
        setLoadingWatchlist(false)
      }
    }

    loadWatchlist()
  }, [activeTab, selectedPortfolio])


  return (
    <div className="flex flex-col h-screen bg-slate-950">
      {/* Main content */}
      <div className="flex flex-1 h-full overflow-hidden">
        {/* Left sidebar - Portfolio & Holdings */}
        <div className="w-80 bg-slate-900 border-r border-slate-800 flex flex-col overflow-hidden">
          {/* Portfolio selector */}
          <div className="px-4 py-4 border-b border-slate-800 flex-shrink-0 space-y-3">
            <div className="text-sm font-bold text-white">Portfolio</div>
            {loadingPortfolios ? (
              <div className="text-xs text-slate-400">Loading portfolios...</div>
            ) : portfolios.length === 0 ? (
              <div className="text-xs text-slate-400">No portfolios available</div>
            ) : (
              <select
                value={selectedPortfolio}
                onChange={(e) => setSelectedPortfolio(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 text-white rounded px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
              >
                {portfolios.map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Tabs */}
          <div className="px-4 py-0 border-b border-slate-800 flex-shrink-0 flex gap-0">
            <button
              onClick={() => setActiveTab('holdings')}
              className={`flex-1 py-3 px-4 text-sm font-medium border-b-2 transition ${
                activeTab === 'holdings'
                  ? 'border-purple-600 text-white'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              Holdings
            </button>
            <button
              onClick={() => setActiveTab('watchlist')}
              className={`flex-1 py-3 px-4 text-sm font-medium border-b-2 transition ${
                activeTab === 'watchlist'
                  ? 'border-purple-600 text-white'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              Watchlist
            </button>
          </div>

          {/* Holdings header */}
          {activeTab === 'holdings' && (
            <div className="px-4 py-3 border-b border-slate-800 flex-shrink-0">
              <div className="grid grid-cols-4 gap-2 text-xs text-slate-400">
                <div>Symbol</div>
                <div className="text-right">Price</div>
                <div className="text-right">Gain</div>
                <div className="text-right">%</div>
              </div>
            </div>
          )}

          {/* Watchlist header */}
          {activeTab === 'watchlist' && (
            <div className="px-4 py-3 border-b border-slate-800 flex-shrink-0">
              <div className="grid grid-cols-4 gap-2 text-xs">
                <button
                  onClick={() => handleSort('ticker')}
                  className={`text-left cursor-pointer hover:text-white transition ${
                    sortBy === 'ticker' ? 'text-white font-bold' : 'text-slate-400'
                  }`}
                >
                  Symbol {sortBy === 'ticker' && (sortDirection === 'asc' ? '↑' : '↓')}
                </button>
                <button
                  onClick={() => handleSort('price')}
                  className={`text-right cursor-pointer hover:text-white transition ${
                    sortBy === 'price' ? 'text-white font-bold' : 'text-slate-400'
                  }`}
                >
                  Price {sortBy === 'price' && (sortDirection === 'asc' ? '↑' : '↓')}
                </button>
                <button
                  onClick={() => handleSort('score')}
                  className={`text-right cursor-pointer hover:text-white transition ${
                    sortBy === 'score' ? 'text-white font-bold' : 'text-slate-400'
                  }`}
                >
                  Score {sortBy === 'score' && (sortDirection === 'asc' ? '↑' : '↓')}
                </button>
                <button
                  onClick={() => handleSort('entry')}
                  className={`text-right cursor-pointer hover:text-white transition ${
                    sortBy === 'entry' ? 'text-white font-bold' : 'text-slate-400'
                  }`}
                >
                  Entry {sortBy === 'entry' && (sortDirection === 'asc' ? '↑' : '↓')}
                </button>
              </div>
            </div>
          )}

          {/* Holdings list */}
          {activeTab === 'holdings' && (
            <div className="flex-1 overflow-y-auto">
              {loadingHoldings ? (
                <div className="px-4 py-4 text-xs text-slate-400">Loading holdings...</div>
              ) : holdings.length === 0 ? (
                <div className="px-4 py-4 text-xs text-slate-400">No holdings in portfolio</div>
              ) : (
                holdings.map((holding) => (
                  <div
                    key={holding.ticker}
                    onClick={() => {
                      setSelectedTicker(holding.ticker)
                      navigate(`/chart/${holding.ticker}`)
                    }}
                    className={`px-4 py-3 border-b border-slate-800 cursor-pointer hover:bg-slate-800/50 transition ${
                      selectedTicker === holding.ticker ? 'bg-purple-600/20' : ''
                    }`}
                  >
                    <div className="grid grid-cols-4 gap-2 items-center">
                      <div className="font-medium text-white text-sm">{holding.ticker}</div>
                      <div className="text-right text-white text-sm">{holding.current_price.toFixed(2)}</div>
                      <div className={`text-right text-xs ${holding.position_gain >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {holding.position_gain >= 0 ? '+' : ''}{holding.position_gain.toFixed(2)}
                      </div>
                      <div className={`text-right text-xs ${holding.position_gain_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {holding.position_gain_pct >= 0 ? '+' : ''}{holding.position_gain_pct.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Watchlist list */}
          {activeTab === 'watchlist' && (
            <div className="flex-1 overflow-y-auto">
              {loadingWatchlist ? (
                <div className="px-4 py-4 text-xs text-slate-400">Loading watchlist...</div>
              ) : watchlist.length === 0 ? (
                <div className="px-4 py-4 text-xs text-slate-400">Watchlist is empty</div>
              ) : (
                sortedWatchlist.map((item) => (
                  <div
                    key={item.ticker}
                    onClick={() => {
                      setSelectedTicker(item.ticker)
                      navigate(`/chart/${item.ticker}`)
                    }}
                    className={`px-4 py-3 border-b border-slate-800 cursor-pointer hover:bg-slate-800/50 transition ${
                      selectedTicker === item.ticker ? 'bg-purple-600/20' : ''
                    }`}
                  >
                    <div className="grid grid-cols-4 gap-2 items-center">
                      <div className="font-medium text-white text-sm">{item.ticker}</div>
                      <div className="text-right text-white text-sm">{parseFloat(item.close).toFixed(2)}</div>
                      <div className="text-right text-xs text-purple-400 font-semibold">{(parseFloat(item.signal_score) * 100).toFixed(0)}</div>
                      <div className="text-right text-xs text-blue-400 font-semibold">{item.entry_score || '—'}</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Portfolio stats */}
          {activeTab === 'holdings' && selectedPortfolio && !loadingHoldings && (
            <div className="px-4 py-4 border-t border-slate-800 text-xs space-y-2 flex-shrink-0">
              <div className="flex justify-between">
                <span className="text-slate-400">Positions</span>
                <span className="text-white">{holdings.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Total Value</span>
                <span className="text-white">${(holdings.reduce((sum, h) => sum + h.position_value, 0) / 1000).toFixed(1)}K</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Total Gain</span>
                <span className={holdings.reduce((sum, h) => sum + h.position_gain, 0) >= 0 ? 'text-green-400' : 'text-red-400'}>
                  ${(holdings.reduce((sum, h) => sum + h.position_gain, 0)).toFixed(0)}
                </span>
              </div>
            </div>
          )}

          {/* Watchlist stats */}
          {activeTab === 'watchlist' && selectedPortfolio && !loadingWatchlist && (
            <div className="px-4 py-4 border-t border-slate-800 text-xs space-y-2 flex-shrink-0">
              <div className="flex justify-between">
                <span className="text-slate-400">Watchlist Items</span>
                <span className="text-white">{watchlist.length}</span>
              </div>
            </div>
          )}
        </div>

        {/* Center - Chart */}
        <div className="flex-1 h-full bg-slate-950 overflow-hidden">
          <TradingChart timeframe={timeframe} title={selectedTicker} ticker={selectedTicker} selectedIndicators={selectedIndicators} visibleWindow={visibleWindow} />
        </div>

        {/* Right sidebar - Controls */}
        <div className="w-48 bg-slate-900 border-l border-slate-800 p-4 overflow-y-auto space-y-4">
          {/* Timeframe selector */}
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase mb-2">Timeframe</div>
            <div className="grid grid-cols-3 gap-1">
              {['1D', '1W', '1M', '3M', '6M', '1Y'].map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`py-1 px-2 text-xs rounded transition ${
                    timeframe === tf
                      ? 'bg-purple-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {/* Visible Window selector */}
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase mb-2">Window</div>
            <div className="grid grid-cols-3 gap-1">
              {(['1M', '3M', '6M', 'YTD', '1Y', '2Y'] as const).map((window) => (
                <button
                  key={window}
                  onClick={() => setVisibleWindow(window)}
                  className={`py-1 px-2 text-xs rounded transition ${
                    visibleWindow === window
                      ? 'bg-purple-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                  }`}
                >
                  {window}
                </button>
              ))}
            </div>
          </div>

          {/* Indicators */}
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase mb-2">Indicators</div>
            <div className="space-y-2">
              {['MA 20', 'MA 50', 'MA 200', 'RSI 14', 'MACD'].map((indicator) => (
                <label key={indicator} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    className="rounded border-slate-600"
                    checked={selectedIndicators.has(indicator)}
                    onChange={() => toggleIndicator(indicator)}
                  />
                  <span className="text-sm text-slate-300">{indicator}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Chart Type */}
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase mb-2">Chart Type</div>
            <div className="space-y-1">
              {['Candlestick', 'Line', 'Bars'].map((type) => (
                <button
                  key={type}
                  className={`w-full text-left px-3 py-2 text-sm rounded transition ${
                    type === 'Candlestick'
                      ? 'bg-purple-600 text-white'
                      : 'text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

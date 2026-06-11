import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

interface Universe {
  id: string
  name: string
  count?: number
}

interface Ticker {
  symbol: string
  name?: string
  sector?: string
  industry?: string
  market_cap?: string
  price?: string
  change?: string
  revenue?: string
  isin?: string
  currency?: string
}

const ASSET_CATEGORIES = [
  { id: 'stocks', label: 'Stocks', icon: '📈' },
  { id: 'etfs', label: 'ETFs', icon: '💱' },
  { id: 'funds', label: 'Funds', icon: '🏦' },
  { id: 'indices', label: 'Indices', icon: '📊' },
  { id: 'currencies', label: 'Currencies', icon: '💱' },
]

const MARKET_FILTERS = [
  { id: 'all', label: 'All Markets', icon: '🌍' },
  { id: 'europe', label: 'Europe', icon: '🇪🇺', universes: ['cac40', 'srd', 'enx_large', 'enx_mid', 'enx_small', 'xetra', 'etf_pea', 'etf_pea_full', 'etf_pea_test', 'etf_fr'] },
  { id: 'usa', label: 'USA', icon: '🇺🇸', universes: ['nasdaq_100', 'nasdaq_tech', 'sp_25'] },
  { id: 'indices', label: 'Indices', icon: '📊', universes: ['index'] },
  { id: 'other', label: 'Other', icon: '🌐', universes: ['single'] },
]

export default function Data() {
  const navigate = useNavigate()
  const [universes, setUniverses] = useState<Universe[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string>('stocks')
  const [selectedUniverse, setSelectedUniverse] = useState<string | null>(null)
  const [tickers, setTickers] = useState<Ticker[]>([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedMarket, setSelectedMarket] = useState<string>('all')
  const [showMarketDropdown, setShowMarketDropdown] = useState(false)

  // Load universes on mount
  useEffect(() => {
    loadUniverses()
  }, [])

  // Load tickers for selected universe
  useEffect(() => {
    if (selectedUniverse) {
      loadTickers(selectedUniverse)
    }
  }, [selectedUniverse])

  const loadUniverses = async () => {
    try {
      setLoading(true)
      const response = await fetch(`http://192.168.0.130:6501/api/v1/data/universes/list`)
      if (response.ok) {
        const data = await response.json()
        const universeList = data.universes || []
        setUniverses(universeList)
        // Auto-select first universe
        if (universeList.length > 0) {
          setSelectedUniverse(universeList[0].id)
        }
      }
    } catch (err) {
      console.error('Failed to load universes:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadTickers = async (universe: string) => {
    try {
      setLoading(true)
      const response = await fetch(`http://192.168.0.130:6501/api/v1/data/universe/${universe}`)
      if (response.ok) {
        const data = await response.json()
        setTickers(data.tickers || [])
      }
    } catch (err) {
      console.error('Failed to load tickers:', err)
    } finally {
      setLoading(false)
    }
  }

  // Filter universes by selected market
  const filteredUniverses = universes.filter(uni => {
    if (selectedMarket === 'all') return true
    const market = MARKET_FILTERS.find(m => m.id === selectedMarket)
    return market?.universes?.includes(uni.id) || false
  })

  const filteredTickers = tickers.filter(ticker =>
    searchQuery === '' ||
    ticker.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
    ticker.name?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const currentMarket = MARKET_FILTERS.find(m => m.id === selectedMarket)

  return (
    <div className="flex-1 bg-slate-950 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Data Management</h1>
          <p className="text-sm text-slate-400 mt-1">Browse and manage financial data by asset type</p>
        </div>
        <button
          onClick={() => navigate('/data/universes')}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium transition"
        >
          📦 Manage Universes
        </button>
      </div>

      {/* Main content */}
      <div className="flex-1 flex gap-4 p-6 overflow-hidden">
        {/* Left Panel */}
        <div className="w-80 flex flex-col border border-slate-800 rounded-lg bg-slate-900">
          {/* Asset Categories */}
          <div className="border-b border-slate-800">
            <div className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Asset Types</div>
            <div className="space-y-1 px-2 pb-3">
              {ASSET_CATEGORIES.map(cat => (
                <button
                  key={cat.id}
                  onClick={() => {
                    setSelectedCategory(cat.id)
                    setSelectedUniverse(null)
                    setTickers([])
                    setSearchQuery('')
                  }}
                  className={`w-full text-left px-3 py-2 rounded text-sm transition ${
                    selectedCategory === cat.id
                      ? 'bg-purple-600/30 text-purple-300'
                      : 'text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  <span className="mr-2">{cat.icon}</span>
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          {/* Universes Header */}
          <div className="px-4 py-3 border-b border-slate-800 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Universes ({filteredUniverses.length})
          </div>

          {/* Universes List */}
          <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
            {loading && universes.length === 0 ? (
              <div className="text-center text-slate-500 py-8">Loading universes...</div>
            ) : filteredUniverses.length === 0 ? (
              <div className="text-center text-slate-500 py-8">No universes in this market</div>
            ) : (
              filteredUniverses.map(universe => (
                <button
                  key={universe.id}
                  onClick={() => setSelectedUniverse(universe.id)}
                  className={`w-full text-left px-3 py-2 rounded transition ${
                    selectedUniverse === universe.id
                      ? 'bg-purple-600/30 text-purple-300 border border-purple-500'
                      : 'text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">{universe.name}</div>
                      <div className="text-xs text-slate-500">{universe.count || 0} tickers</div>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Right Panel */}
        <div className="flex-1 flex flex-col border border-slate-800 rounded-lg bg-slate-900 min-h-0">
          {/* Market Selector + Search Bar (inline) */}
          <div className="px-4 py-3 border-b border-slate-800 flex gap-3 items-center">
            {/* Market Selector */}
            <div className="relative w-48">
              <button
                onClick={() => setShowMarketDropdown(!showMarketDropdown)}
                className="w-full px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white rounded text-sm flex items-center justify-between transition"
              >
                <span>
                  <span className="text-lg mr-2">{currentMarket?.icon}</span>
                  {currentMarket?.label}
                </span>
                <span className={`text-xs transition ${showMarketDropdown ? 'rotate-180' : ''}`}>▼</span>
              </button>

              {/* Dropdown Menu */}
              {showMarketDropdown && (
                <div className="absolute top-full mt-2 left-0 right-0 bg-slate-800 border border-slate-700 rounded shadow-lg z-50">
                  {MARKET_FILTERS.map(market => (
                    <button
                      key={market.id}
                      onClick={() => {
                        setSelectedMarket(market.id)
                        setShowMarketDropdown(false)
                      }}
                      className={`w-full text-left px-3 py-2 text-sm transition ${
                        selectedMarket === market.id
                          ? 'bg-purple-600/30 text-purple-300'
                          : 'text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      <span className="text-lg mr-2">{market.icon}</span>
                      {market.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Search */}
            <input
              type="text"
              placeholder="Search tickers or names..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
            />
          </div>

          {/* Table */}
          <div className="flex-1 overflow-auto">
            {loading ? (
              <div className="flex items-center justify-center h-full text-slate-400">
                Loading tickers...
              </div>
            ) : filteredTickers.length === 0 ? (
              <div className="flex items-center justify-center h-full text-slate-400">
                No tickers found
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-slate-800 border-b border-slate-700">
                  <tr>
                    <th className="px-4 py-3 text-left text-slate-300 font-semibold">Symbol</th>
                    <th className="px-4 py-3 text-left text-slate-300 font-semibold">Name</th>
                    <th className="px-4 py-3 text-left text-slate-300 font-semibold">Sector</th>
                    <th className="px-4 py-3 text-left text-slate-300 font-semibold">Industry</th>
                    <th className="px-4 py-3 text-right text-slate-300 font-semibold">Price</th>
                    <th className="px-4 py-3 text-right text-slate-300 font-semibold">Market Cap</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {filteredTickers.map(ticker => (
                    <tr key={ticker.symbol} className="hover:bg-slate-800/50 transition">
                      <td className="px-4 py-3 font-medium text-purple-300">{ticker.symbol}</td>
                      <td className="px-4 py-3 text-slate-300">{ticker.name || '-'}</td>
                      <td className="px-4 py-3 text-slate-400">{ticker.sector || '-'}</td>
                      <td className="px-4 py-3 text-slate-400">{ticker.industry || '-'}</td>
                      <td className="px-4 py-3 text-right text-slate-400">{ticker.price || '-'}</td>
                      <td className="px-4 py-3 text-right text-slate-400">{ticker.market_cap || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Footer */}
          {filteredTickers.length > 0 && (
            <div className="px-4 py-3 border-t border-slate-800 text-xs text-slate-500">
              Showing {filteredTickers.length} of {tickers.length} tickers
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

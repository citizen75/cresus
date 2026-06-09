import { usePortfolioContext } from '@/context/PortfolioContext'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useEnrichedPositions } from '@/hooks/useEnrichedPositions'
import PositionModal from './PositionModal'
import CardChart from '@/components/CardChart'
import TradingChart from '@/components/TradingChart'
import { PortfolioHoldingsTable } from './PortfolioHoldingsTable'
import { api } from '@/services/api'
import { formatCurrency } from '@/utils/currency'

interface HoldingsViewProps {
  name: string
}

export default function HoldingsView({ name }: HoldingsViewProps) {
  const navigate = useNavigate()
  const { data, isLoading: isContextLoading, refreshData } = usePortfolioContext()
  const { details, currentPrices: priceData, history } = data
  const isPricesLoading = isContextLoading
  const pricesError = null
  const [activeTab, setActiveTab] = useState('positions')
  const [viewMode, setViewMode] = useState<'table' | 'charts'>('table')
  const [timeframe, setTimeframe] = useState<'1W' | '1M' | '3M' | 'YTD' | 'ALL'>('1M')
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null)
  const [positionModalMode, setPositionModalMode] = useState<'buy' | 'sell' | null>(null)
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
  const [selectedPositionData, setSelectedPositionData] = useState<any>(null)
  const [sortColumn, setSortColumn] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const [historicalData, setHistoricalData] = useState<Record<string, any[]>>({})
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [sectorFilter, setSectorFilter] = useState<string>('All sectors')
  const [chartPosition, setChartPosition] = useState<any>(null)
  const [hoverData, setHoverData] = useState<any>(null)

  const rawPositions = priceData?.positions || []
  const { enrichedPositions, fundamentalData } = useEnrichedPositions(rawPositions, name)
  const positions = enrichedPositions.length > 0 ? enrichedPositions : rawPositions
  const totalValue = priceData?.total_value || 0
  const cash = priceData?.cash || 0
  const totalPortfolioValue = priceData?.total_portfolio_value || totalValue

  // Calculate days based on timeframe
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

  // Filter data by timeframe
  const filterDataByTimeframe = (data: any[], tf: string) => {
    if (tf === 'ALL') return data

    let cutoffDate = new Date()

    if (tf === 'YTD') {
      // Year To Date: from Jan 1 to today
      cutoffDate = new Date(cutoffDate.getFullYear(), 0, 1)
    } else {
      // Other periods: N days back from today
      const days = getDaysForTimeframe(tf)
      cutoffDate.setDate(cutoffDate.getDate() - days)
    }

    const filtered = data.filter((item: any) => {
      const itemDate = new Date(item.date)
      return itemDate >= cutoffDate
    })

    console.log(`Filter ${tf}: cutoff=${cutoffDate.toISOString()}, input=${data.length}, output=${filtered.length}`)
    return filtered
  }

  // Load historical data for cards view (fetch full history once)
  useEffect(() => {
    const loadHistoricalData = async () => {
      const data: Record<string, any[]> = {}
      const days = 1825 // Always fetch full history (~5 years), filter on demand
      for (const pos of rawPositions) {
        try {
          const result = await api.getHistoricalData(pos.ticker, days)

          // Handle different response structures
          let historyArray = []
          if (result && Array.isArray(result)) {
            historyArray = result
          } else if (result && result.history && Array.isArray(result.history)) {
            historyArray = result.history
          } else if (result && result.data && Array.isArray(result.data)) {
            historyArray = result.data
          }

          if (historyArray.length > 0) {
            data[pos.ticker] = historyArray.map((item: any) => ({
              date: item.date || item.timestamp || item.Date,
              close: parseFloat(item.close || item.Close),
              open: item.open || item.Open,
              high: item.high || item.High,
              low: item.low || item.Low,
              volume: item.volume || item.Volume,
            }))
          } else {
            // No data found, try to fetch it
            console.log(`No cached data for ${pos.ticker}, attempting to fetch...`)
            // We'll set empty array for now and user can refresh
          }
        } catch (error) {
          console.error(`Failed to load historical data for ${pos.ticker}:`, error)
        }
      }
      setHistoricalData(data)
    }

    if (rawPositions.length > 0) {
      loadHistoricalData()
    }
  }, [rawPositions])

  // Handle ESC key to close chart modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && chartPosition) {
        setChartPosition(null)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [chartPosition])

  // Sorting logic
  const getSortedPositions = () => {
    // First, filter by search query and sector
    let filtered = positions.filter((pos: any) => {
      // Search filter
      const matchesSearch = searchQuery === '' ||
        pos.ticker.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (pos.company_name || '').toLowerCase().includes(searchQuery.toLowerCase())

      // Sector filter
      const matchesSector = sectorFilter === 'All sectors' || pos.sector === sectorFilter

      return matchesSearch && matchesSector
    })

    // Then sort if needed
    if (!sortColumn) return filtered

    return filtered.sort((a: any, b: any) => {
      let aVal, bVal

      switch (sortColumn) {
        case 'symbol':
          aVal = a.ticker.toLowerCase()
          bVal = b.ticker.toLowerCase()
          break
        case 'company':
          aVal = (a.company_name || a.ticker).toLowerCase()
          bVal = (b.company_name || b.ticker).toLowerCase()
          break
        case 'sector':
          aVal = (a.sector || 'unknown').toLowerCase()
          bVal = (b.sector || 'unknown').toLowerCase()
          break
        case 'type':
          aVal = (a.asset_type || 'stock').toLowerCase()
          bVal = (b.asset_type || 'stock').toLowerCase()
          break
        case 'weight':
          aVal = (a.position_value / totalValue) * 100
          bVal = (b.position_value / totalValue) * 100
          break
        case 'shares':
          aVal = a.quantity
          bVal = b.quantity
          break
        case 'avg_cost':
          aVal = a.avg_entry_price
          bVal = b.avg_entry_price
          break
        case 'price':
          aVal = a.current_price
          bVal = b.current_price
          break
        case 'daily_change':
          const aFund = fundamentalData[a.ticker] || {}
          const bFund = fundamentalData[b.ticker] || {}
          const aPrevClose = aFund.previous_close || a.current_price
          const bPrevClose = bFund.previous_close || b.current_price
          aVal = a.current_price - aPrevClose
          bVal = b.current_price - bPrevClose
          break
        case 'market_value':
          aVal = a.position_value
          bVal = b.position_value
          break
        case 'unrealized_pnl':
          aVal = a.position_gain
          bVal = b.position_gain
          break
        case 'pnl_pct':
          aVal = a.position_gain_pct
          bVal = b.position_gain_pct
          break
        default:
          return 0
      }

      // String comparison
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDirection === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      }

      // Numeric comparison
      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : aVal < bVal ? -1 : 0
      } else {
        return bVal > aVal ? 1 : bVal < aVal ? -1 : 0
      }
    })
  }

  const handleColumnSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('asc')
    }
  }

  const getSortIndicator = (column: string) => {
    if (sortColumn !== column) return ''
    return sortDirection === 'asc' ? ' ↑' : ' ↓'
  }

  const sortedPositions = getSortedPositions()

  // Calculate sector exposure from positions
  const sectorMap = new Map<string, number>()
  positions.forEach((pos: any) => {
    const sector = pos.sector || 'Unknown'
    sectorMap.set(sector, (sectorMap.get(sector) || 0) + pos.position_value)
  })

  // Calculate summary metrics
  const unrealizedPNL = positions.reduce((sum: number, pos: any) => sum + (pos.position_gain || 0), 0)
  const unrealizedPNLPercent = totalValue > 0 ? (unrealizedPNL / (totalValue - unrealizedPNL)) * 100 : 0

  // Calculate Day P&L from history
  let dayPNL = 0
  let dayPNLPercent = 0
  if (history && history.history && Array.isArray(history.history) && history.history.length >= 2) {
    const historyData = history.history
    const today = historyData[historyData.length - 1]
    const yesterday = historyData[historyData.length - 2]
    if (today && yesterday && typeof today.value === 'number' && typeof yesterday.value === 'number') {
      dayPNL = today.value - yesterday.value
      dayPNLPercent = yesterday.value > 0 ? (dayPNL / yesterday.value) * 100 : 0
    }
  }

  const cashPercent = totalPortfolioValue > 0 ? (cash / totalPortfolioValue) * 100 : 0
  const invested = totalValue
  const investedPercent = totalPortfolioValue > 0 ? (totalValue / totalPortfolioValue) * 100 : 0

  const tabs = ['Overview', 'Positions', 'Allocation', 'Performance', 'Risk', 'Exposure', 'Income']

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Holdings</h2>
          <p className="text-slate-400 text-sm mt-1">
            {isPricesLoading ? 'Loading real-time prices...' : 'Manage your investment positions'}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => {
              setPositionModalMode('buy')
              setSelectedTicker(null)
            }}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition text-sm"
          >
            + Buy
          </button>
          {selectedPosition && (
            <button
              onClick={() => {
                setPositionModalMode('sell')
                setSelectedTicker(selectedPosition)
              }}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition text-sm"
            >
              📉 Sell
            </button>
          )}
          <button
            onClick={() => navigate(`/portfolios/${encodeURIComponent(name)}/holdings/transactions`)}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-medium transition text-sm"
          >
            📋 Transactions
          </button>
          <button className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-medium transition text-sm">
            Rebalance
          </button>
        </div>
      </div>

      {/* Error Message */}
      {pricesError && (
        <div className="p-4 bg-red-900/30 border border-red-800 rounded text-red-400 text-sm">
          Failed to load real-time prices: {pricesError instanceof Error ? pricesError.message : 'Unknown error'}
        </div>
      )}

      {/* Portfolio Summary Cards */}
      <div className="grid grid-cols-5 gap-4">
        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">Total Value</p>
          <p className="text-white font-bold text-2xl">{formatCurrency(totalPortfolioValue, details?.currency || 'USD')}</p>
          <p className="text-green-400 text-sm mt-1">+{formatCurrency(12540.32, details?.currency || 'USD')} (+1.87%)</p>
        </div>

        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">Day P&L</p>
          <p className={`${dayPNL >= 0 ? 'text-green-400' : 'text-red-400'} font-bold text-2xl`}>{dayPNL >= 0 ? '+' : ''}{formatCurrency(Math.abs(dayPNL), details?.currency || 'USD')}</p>
          <p className={`${dayPNL >= 0 ? 'text-green-400' : 'text-red-400'} text-sm mt-1`}>({dayPNL >= 0 ? '+' : ''}{dayPNLPercent.toFixed(2)}%)</p>
        </div>

        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">Unrealized P&L</p>
          <p className="text-green-400 font-bold text-2xl">+{formatCurrency(unrealizedPNL, details?.currency || 'USD')}</p>
          <p className="text-green-400 text-sm mt-1">(+{unrealizedPNLPercent.toFixed(2)}%)</p>
        </div>

        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">Cash</p>
          <p className="text-white font-bold text-2xl">{formatCurrency(cash, details?.currency || 'USD')}</p>
          <p className="text-slate-400 text-sm mt-1">({cashPercent.toFixed(1)}%)</p>
        </div>

        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">Invested</p>
          <p className="text-white font-bold text-2xl">{formatCurrency(invested, details?.currency || 'USD')}</p>
          <p className="text-slate-400 text-sm mt-1">({investedPercent.toFixed(1)}%)</p>
        </div>
      </div>

      {/* Main Content */}
      <div>
        {/* Holdings Table */}
        <div>
          {/* Tab Navigation */}
          <div className="border-b border-slate-800 mb-6">
            <div className="flex gap-6 overflow-x-auto">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab.toLowerCase())}
                  className={`px-1 py-3 font-medium text-sm transition border-b-2 whitespace-nowrap ${
                    activeTab === tab.toLowerCase()
                      ? 'border-purple-600 text-white'
                      : 'border-transparent text-slate-400 hover:text-slate-300'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Filters - Only for Positions tab */}
          {activeTab === 'positions' && (
            <div className="flex gap-3 mb-4 items-center">
              {/* Search and Filters */}
              <div className="flex-1 relative">
                <input
                  type="text"
                  placeholder="Search by symbol or company..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg focus:outline-none focus:border-purple-600"
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500">🔍</span>
              </div>

              <select className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:border-slate-600 transition whitespace-nowrap">
                <option>All positions</option>
                <option>Long only</option>
                <option>Short only</option>
              </select>

              <select
                value={sectorFilter}
                onChange={(e) => setSectorFilter(e.target.value)}
                className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:border-slate-600 transition whitespace-nowrap"
              >
                <option>All sectors</option>
                {Array.from(sectorMap.keys())
                  .sort()
                  .map((sector: string) => (
                    <option key={sector} value={sector}>
                      {sector}
                    </option>
                  ))}
              </select>

              <select className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:border-slate-600 transition whitespace-nowrap">
                <option>All assets</option>
                {Array.from(new Set(positions.map((p: any) => p.asset_type || 'Stock')) as Set<string>)
                  .sort()
                  .map((type: string) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
              </select>

              <button className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 transition flex-shrink-0">
                ⚙️
              </button>

              {/* Table/Charts Toggle */}
              <div className="flex gap-2 bg-slate-800 border border-slate-700 rounded-lg p-1 flex-shrink-0">
                <button
                  onClick={() => setViewMode('table')}
                  className={`px-4 py-1.5 rounded transition font-medium text-sm ${
                    viewMode === 'table'
                      ? 'bg-purple-600 text-white'
                      : 'text-slate-400 hover:text-slate-300'
                  }`}
                >
                  📊 Table
                </button>
                <button
                  onClick={() => setViewMode('charts')}
                  className={`px-4 py-1.5 rounded transition font-medium text-sm ${
                    viewMode === 'charts'
                      ? 'bg-purple-600 text-white'
                      : 'text-slate-400 hover:text-slate-300'
                  }`}
                >
                  📈 Charts
                </button>
              </div>

              {/* Timeframe Dropdown - Only visible in charts mode */}
              {viewMode === 'charts' && (
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value as '1W' | '1M' | '3M' | 'YTD' | 'ALL')}
                  className="px-4 py-1.5 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:border-slate-600 transition font-medium text-sm flex-shrink-0"
                >
                  <option value="1W">1W</option>
                  <option value="1M">1M</option>
                  <option value="3M">3M</option>
                  <option value="YTD">YTD</option>
                  <option value="ALL">ALL</option>
                </select>
              )}
            </div>
          )}

          {/* Tab Content - Table View */}
          {activeTab === 'positions' && viewMode === 'table' && (
            <PortfolioHoldingsTable
              positions={positions}
              totalValue={totalValue}
              currency={details?.currency || 'USD'}
              fundamentalData={fundamentalData}
              selectedPosition={selectedPosition}
              onSelectPosition={(ticker) => {
                setSelectedPosition(ticker)
                const pos = positions.find((p: any) => p.ticker === ticker)
                if (pos) setChartPosition(pos)
              }}
              showSearch={false}
              showActions={true}
              externalSearchQuery={searchQuery}
              onSearchChange={setSearchQuery}
            />
          )}

          {/* Cards View - Position Cards */}
          {activeTab === 'positions' && viewMode === 'charts' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {positions.map((pos: any) => (
              <div key={pos.ticker} className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden hover:border-purple-600/50 transition">
                {/* Card Header */}
                <div className="bg-slate-800/50 border-b border-slate-800 p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="text-white font-bold text-lg">{pos.company_name || pos.ticker}</p>
                      <p className="text-slate-400 text-xs">{pos.ticker}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-green-400">{((pos.position_gain / pos.position_value) * 100).toFixed(1)}%</p>
                      <p className="text-slate-400 text-xs">Return</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex gap-2 items-center flex-wrap">
                      <span className="px-2 py-1 rounded text-xs font-medium bg-slate-800/30 text-slate-400">
                        {pos.quantity} shares @ €{pos.avg_entry_price.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Chart */}
                {historicalData[pos.ticker] && historicalData[pos.ticker].length > 0 ? (
                  <CardChart
                    data={filterDataByTimeframe(historicalData[pos.ticker], timeframe)}
                    ticker={pos.ticker}
                    showVariation={false}
                  />
                ) : (
                  <div className="p-4 h-48 bg-slate-800/20 flex flex-col items-center justify-center gap-2">
                    <p className="text-slate-500 text-sm">No historical data</p>
                    <p className="text-slate-600 text-xs">Run: cresus data fetch history {pos.ticker}</p>
                  </div>
                )}

                {/* Price Range Row - First/Var/Last */}
                {historicalData[pos.ticker] && historicalData[pos.ticker].length > 0 && (() => {
                  const filteredData = filterDataByTimeframe(historicalData[pos.ticker], timeframe)
                  const firstPrice = filteredData[0]?.close
                  const lastPrice = filteredData[filteredData.length - 1]?.close
                  const change = firstPrice ? ((lastPrice - firstPrice) / firstPrice) * 100 : 0
                  return (
                    <div className="border-t border-slate-800 px-4 py-3 bg-slate-800/30">
                      <div className="flex justify-between items-center text-xs">
                        <div className="flex flex-col items-center flex-1">
                          <p className="text-slate-500 text-xs mb-1">90D Low</p>
                          <p className="text-white font-medium">€{firstPrice?.toFixed(3)}</p>
                        </div>
                        <div className="flex flex-col items-center flex-1">
                          <p className="text-slate-500 text-xs mb-1">Current</p>
                          <p className={`font-medium ${change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            €{pos.current_price.toFixed(2)}
                          </p>
                        </div>
                        <div className="flex flex-col items-center flex-1">
                          <p className="text-slate-500 text-xs mb-1">90D High</p>
                          <p className="text-white font-medium">€{lastPrice?.toFixed(3)}</p>
                        </div>
                      </div>
                    </div>
                  )
                })()}

                {/* Card Footer */}
                <div className="border-t border-slate-800 p-4 space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">Position Value</span>
                    <span className="text-white font-medium">€{pos.position_value.toLocaleString('de-DE', { maximumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">Unrealized P&L</span>
                    <span className={`font-medium ${pos.position_gain >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      €{pos.position_gain.toLocaleString('de-DE', { maximumFractionDigits: 2 })}
                    </span>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedTicker(pos.ticker)
                      setSelectedPositionData(pos)
                      setPositionModalMode('sell')
                    }}
                    className="w-full mt-3 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded text-xs font-medium transition"
                  >
                    Manage Position
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        </div>
      </div>

      {/* Chart Modal */}
      {chartPosition && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-lg border border-slate-800 w-full max-w-6xl h-screen max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
              <h2 className="text-2xl font-bold text-white">
                {chartPosition.company_name && (
                  <span className="text-slate-400 font-normal">{chartPosition.company_name} </span>
                )}
                {chartPosition.ticker}
              </h2>
              <button
                onClick={() => setChartPosition(null)}
                className="text-slate-400 hover:text-white transition text-2xl"
              >
                ✕
              </button>
            </div>

            {/* Chart Container */}
            <div className="flex-1 overflow-hidden">
              <TradingChart
                timeframe="1Y"
                ticker={chartPosition.ticker}
                visibleWindow="1Y"
                onCursorMove={setHoverData}
              />
            </div>
          </div>
        </div>
      )}

      {/* Position Modal */}
      <PositionModal
        isOpen={positionModalMode !== null}
        mode={positionModalMode}
        ticker={selectedTicker || undefined}
        positionData={selectedPositionData}
        onClose={() => {
          setPositionModalMode(null)
          setSelectedTicker(null)
          setSelectedPositionData(null)
        }}
        onSuccess={() => {
          // Refresh portfolio context data
          refreshData(['currentPrices', 'details', 'history', 'metrics'])
        }}
        portfolioName={name}
      />
    </div>
  )
}

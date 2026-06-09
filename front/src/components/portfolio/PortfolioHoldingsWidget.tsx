import { useState, useEffect } from 'react'
import { PortfolioHoldingsTable } from './PortfolioHoldingsTable'
import CardChart from '@/components/CardChart'
import { getApiBaseUrl } from '@/services/api'

interface PortfolioHoldingsWidgetProps {
  portfolioName: string
  onClose?: () => void
  filterTickers?: string[] // Only show these tickers
}

export default function PortfolioHoldingsWidget({
  portfolioName,
  onClose,
  filterTickers,
}: PortfolioHoldingsWidgetProps) {
  const [positions, setPositions] = useState<any[]>([])
  const [fundamentalData, setFundamentalData] = useState<Record<string, any>>({})
  const [fundamentalCache, setFundamentalCache] = useState<Record<string, any>>({})
  const [historicalData, setHistoricalData] = useState<Record<string, any>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [sectorFilter, setSectorFilter] = useState('All sectors')
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'table' | 'charts'>('table')
  const [timeframe, setTimeframe] = useState<'1W' | '1M' | '3M' | 'YTD' | 'ALL'>('1M')

  // Filter positions if filterTickers is provided (calculate early, before useEffects)
  const filteredPositions = filterTickers && filterTickers.length > 0
    ? positions.filter((pos: any) => filterTickers.includes(pos.ticker))
    : positions

  // Load positions for the portfolio
  useEffect(() => {
    const loadPositionsAndFundamental = async () => {
      if (!portfolioName) return

      setIsLoading(true)
      try {
        const baseUrl = getApiBaseUrl()

        // Fetch positions
        const posResponse = await fetch(`${baseUrl}/api/v1/portfolios/${portfolioName}/positions`)
        if (!posResponse.ok) {
          console.error('Failed to fetch positions')
          setPositions([])
          return
        }

        let posData = await posResponse.json()
        if (!Array.isArray(posData)) {
          posData = posData.positions || []
        }

        let positions = posData
        console.log(`[PortfolioHoldingsWidget] Loaded ${positions.length} positions for ${portfolioName}`)

        if (positions.length > 0) {
          // Fetch fundamental data for all tickers
          const tickers = positions.map((p: any) => p.ticker)
          const fundData: Record<string, any> = {}

          for (const ticker of tickers) {
            // Check cache first
            if (fundamentalCache[ticker]) {
              fundData[ticker] = fundamentalCache[ticker]
            } else {
              try {
                const fundResponse = await fetch(`${baseUrl}/api/v1/data/fundamental/${ticker}`)
                if (fundResponse.ok) {
                  const fundResult = await fundResponse.json()
                  if (fundResult?.data?.quotation) {
                    fundData[ticker] = fundResult.data.quotation
                    console.log(`[PortfolioHoldingsWidget] ✓ ${ticker}: current=${fundResult.data.quotation.current_price}`)
                  }
                }
              } catch (err) {
                console.error(`[PortfolioHoldingsWidget] Failed to fetch fundamental data for ${ticker}:`, err)
              }
            }
          }

          // Update cache for future use
          setFundamentalCache(fundData)

          // Enrich positions with calculated daily changes
          positions = positions.map((pos: any) => {
            const fund = fundData[pos.ticker] || {}
            const currentPrice = pos.current_price || 0
            const previousClose = fund.previous_close || currentPrice

            // Daily change per share: current - previous
            const dailyChange = currentPrice - previousClose
            const dailyChangePct = previousClose && previousClose !== 0 ? ((currentPrice - previousClose) / previousClose) * 100 : 0

            console.log(`[PortfolioHoldingsWidget] ✓ ${pos.ticker}: current=${currentPrice}, prev=${previousClose}, daily=${dailyChange} (${dailyChangePct}%)`)

            return {
              ...pos,
              position_gain: dailyChange,  // Daily change per share
              position_gain_pct: dailyChangePct,
              asset_type: fund.asset_type || 'Stock',
              sector: fund.sector || 'Unknown',
            }
          })

          setPositions(positions)
          setFundamentalData(fundData)
        }
      } catch (err) {
        console.error('Failed to load portfolio positions:', err)
      } finally {
        setIsLoading(false)
      }
    }

    loadPositionsAndFundamental()
  }, [portfolioName])

  // Load historical data for charts
  useEffect(() => {
    const loadHistoricalData = async () => {
      if (!filteredPositions || filteredPositions.length === 0) return

      const data: Record<string, any[]> = {}
      for (const pos of filteredPositions) {
        try {
          const baseUrl = getApiBaseUrl()
          const response = await fetch(`${baseUrl}/api/v1/data/history/${pos.ticker}?days=1825`)
          if (response.ok) {
            const result = await response.json()
            let historyArray = []
            if (Array.isArray(result)) {
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
              }))
            }
          }
        } catch (error) {
          console.error(`Failed to load historical data for ${pos.ticker}:`, error)
        }
      }
      setHistoricalData(data)
    }

    if (viewMode === 'charts') {
      loadHistoricalData()
    }
  }, [filteredPositions, viewMode])

  const getDaysForTimeframe = (tf: string) => {
    switch (tf) {
      case '1W': return 7
      case '1M': return 30
      case '3M': return 90
      case 'YTD': return 365
      case 'ALL': return 1825
      default: return 30
    }
  }

  const filterDataByTimeframe = (data: any[], tf: string) => {
    if (tf === 'ALL') return data
    let cutoffDate = new Date()
    if (tf === 'YTD') {
      cutoffDate = new Date(cutoffDate.getFullYear(), 0, 1)
    } else {
      const days = getDaysForTimeframe(tf)
      cutoffDate.setDate(cutoffDate.getDate() - days)
    }
    return data.filter((item: any) => new Date(item.date) >= cutoffDate)
  }

  const totalValue = filteredPositions.reduce((sum: any, pos: any) => sum + (pos.position_value || 0), 0)

  // Calculate sector map
  const sectorMap = new Map<string, number>()
  filteredPositions.forEach((pos: any) => {
    const sector = pos.sector || 'Unknown'
    sectorMap.set(sector, (sectorMap.get(sector) || 0) + pos.position_value)
  })

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Portfolio Holdings</h3>
        {onClose && (
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition text-lg"
          >
            ✕
          </button>
        )}
      </div>

      {/* Filters - All on one line */}
      <div className="flex gap-2 items-center flex-wrap">
        {/* Search */}
        <div className="flex-1 min-w-[200px] relative">
          <input
            type="text"
            placeholder="Search by symbol or company..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 text-white text-sm placeholder-slate-500 rounded focus:outline-none focus:border-purple-600"
          />
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 text-sm">🔍</span>
        </div>

        {/* Sector Filter */}
        <select
          value={sectorFilter}
          onChange={(e) => setSectorFilter(e.target.value)}
          className="px-3 py-1.5 bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded hover:border-slate-600 transition whitespace-nowrap"
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

        {/* Asset Type Filter */}
        <select className="px-3 py-1.5 bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded hover:border-slate-600 transition whitespace-nowrap">
          <option>All assets</option>
          {Array.from(new Set(positions.map((p: any) => p.asset_type || 'Stock')) as Set<string>)
            .sort()
            .map((type: string) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
        </select>

        {/* Settings */}
        <button className="px-3 py-1.5 bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded hover:bg-slate-700 transition flex-shrink-0">
          ⚙️
        </button>

        {/* Table/Charts Toggle */}
        <div className="flex gap-1 bg-slate-800 border border-slate-700 rounded p-1 flex-shrink-0">
          <button
            onClick={() => setViewMode('table')}
            className={`px-2 py-1 rounded text-xs font-medium transition ${
              viewMode === 'table'
                ? 'bg-purple-600 text-white'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            📊 Table
          </button>
          <button
            onClick={() => setViewMode('charts')}
            className={`px-2 py-1 rounded text-xs font-medium transition ${
              viewMode === 'charts'
                ? 'bg-purple-600 text-white'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            📈 Charts
          </button>
        </div>

        {/* Timeframe Selector - Only visible in charts mode */}
        {viewMode === 'charts' && (
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value as '1W' | '1M' | '3M' | 'YTD' | 'ALL')}
            className="px-3 py-1.5 bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded hover:border-slate-600 transition font-medium flex-shrink-0"
          >
            <option value="1W">1W</option>
            <option value="1M">1M</option>
            <option value="3M">3M</option>
            <option value="YTD">YTD</option>
            <option value="ALL">ALL</option>
          </select>
        )}
      </div>

      {/* Holdings - Table or Charts */}
      <div className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-slate-400">Loading positions...</p>
          </div>
        ) : viewMode === 'table' ? (
          <PortfolioHoldingsTable
            positions={filteredPositions}
            totalValue={totalValue}
            currency="USD"
            fundamentalData={fundamentalData}
            selectedPosition={selectedPosition}
            onSelectPosition={(ticker) => setSelectedPosition(ticker)}
            showSearch={false}
            showActions={true}
            externalSearchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
            showViewToggle={false}
          />
        ) : (
          // Charts View
          <div className="overflow-y-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-2">
              {filteredPositions.map((pos: any) => (
                <div key={pos.ticker} className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden hover:border-purple-600/50 transition">
                  {/* Card Header */}
                  <div className="bg-slate-800/50 border-b border-slate-700 p-3">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="text-white font-bold text-sm">{pos.company_name || pos.ticker}</p>
                        <p className="text-slate-400 text-xs">{pos.ticker}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-bold text-green-400">{((pos.position_gain / pos.position_value) * 100).toFixed(1)}%</p>
                        <p className="text-slate-400 text-xs">Return</p>
                      </div>
                    </div>
                    <div className="text-xs text-slate-400">
                      {pos.quantity} shares @ €{pos.avg_entry_price.toFixed(2)}
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
                    <div className="p-4 h-32 bg-slate-700/20 flex items-center justify-center gap-2">
                      <p className="text-slate-500 text-xs">Loading chart...</p>
                    </div>
                  )}

                  {/* Card Footer */}
                  <div className="border-t border-slate-700 p-3 space-y-2 bg-slate-800/30 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Position Value</span>
                      <span className="text-white font-medium">€{pos.position_value.toLocaleString('de-DE', { maximumFractionDigits: 2 })}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">P&L</span>
                      <span className={`font-medium ${pos.position_gain >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        €{pos.position_gain.toLocaleString('de-DE', { maximumFractionDigits: 2 })}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

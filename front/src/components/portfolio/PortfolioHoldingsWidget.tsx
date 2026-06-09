import { useState, useEffect } from 'react'
import { useEnrichedPositions } from '@/hooks/useEnrichedPositions'
import { PortfolioHoldingsTable } from './PortfolioHoldingsTable'
import CardChart from '@/components/CardChart'
import { ChartModal } from '@/components/ChartModal'
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
  const [rawPositions, setRawPositions] = useState<any[]>([])
  const [historicalData, setHistoricalData] = useState<Record<string, any>>({})
  const [isLoadingPositions, setIsLoadingPositions] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [sectorFilter, setSectorFilter] = useState('All sectors')
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null)
  const [chartModalTicker, setChartModalTicker] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'table' | 'charts'>('table')
  const [timeframe, setTimeframe] = useState<'1W' | '1M' | '3M' | 'YTD' | 'ALL'>('1M')

  // Load raw positions from API
  useEffect(() => {
    const loadPositions = async () => {
      if (!portfolioName) return
      setIsLoadingPositions(true)
      try {
        const baseUrl = getApiBaseUrl()
        const posResponse = await fetch(`${baseUrl}/api/v1/portfolios/${portfolioName}/positions`)
        if (posResponse.ok) {
          let posData = await posResponse.json()
          if (!Array.isArray(posData)) {
            posData = posData.positions || []
          }
          setRawPositions(posData)
        }
      } catch (err) {
        console.error('Failed to load portfolio positions:', err)
      } finally {
        setIsLoadingPositions(false)
      }
    }
    loadPositions()
  }, [portfolioName])

  // Use hook to enrich positions with fundamental data
  const { enrichedPositions, fundamentalData, isLoading: isEnriching } = useEnrichedPositions(rawPositions, portfolioName)
  const isLoading = isLoadingPositions || isEnriching

  // Filter positions if filterTickers is provided (calculate early, before useEffects)
  const filteredPositions = filterTickers && filterTickers.length > 0
    ? enrichedPositions.filter((pos: any) => filterTickers.includes(pos.ticker))
    : enrichedPositions

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
          {Array.from(new Set(filteredPositions.map((p: any) => p.asset_type || 'Stock')) as Set<string>)
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
      <div className="flex-1 overflow-hidden relative">
        {isLoading && (
          <div className="absolute inset-0 bg-slate-900/50 rounded flex items-center justify-center z-10">
            <div className="text-center">
              <div className="inline-block">
                <div className="w-12 h-12 border-4 border-slate-700 border-t-purple-600 rounded-full animate-spin"></div>
              </div>
              <p className="text-slate-400 text-sm mt-3">Loading portfolio...</p>
            </div>
          </div>
        )}
        {!isLoading && viewMode === 'table' ? (
          <PortfolioHoldingsTable
            positions={filteredPositions}
            totalValue={totalValue}
            currency="USD"
            fundamentalData={fundamentalData}
            selectedPosition={selectedPosition}
            onSelectPosition={(ticker) => {
              setSelectedPosition(ticker)
              setChartModalTicker(ticker)
            }}
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

      {/* Chart Modal */}
      {chartModalTicker && (
        <ChartModal
          ticker={chartModalTicker}
          onClose={() => setChartModalTicker(null)}
        />
      )}
    </div>
  )
}

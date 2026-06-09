import { useState, useEffect } from 'react'
import { PortfolioHoldingsTable } from './PortfolioHoldingsTable'
import { getApiBaseUrl } from '@/services/api'

interface PortfolioHoldingsWidgetProps {
  portfolioName: string
  onClose?: () => void
}

export default function PortfolioHoldingsWidget({
  portfolioName,
  onClose,
}: PortfolioHoldingsWidgetProps) {
  const [positions, setPositions] = useState<any[]>([])
  const [fundamentalData, setFundamentalData] = useState<Record<string, any>>({})
  const [fundamentalCache, setFundamentalCache] = useState<Record<string, any>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [sectorFilter, setSectorFilter] = useState('All sectors')
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'table' | 'charts'>('table')

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

  const totalValue = positions.reduce((sum: any, pos: any) => sum + (pos.position_value || 0), 0)

  // Calculate sector map
  const sectorMap = new Map<string, number>()
  positions.forEach((pos: any) => {
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
      </div>

      {/* Holdings Table */}
      <div className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-slate-400">Loading positions...</p>
          </div>
        ) : (
          <PortfolioHoldingsTable
            positions={positions}
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
        )}
      </div>
    </div>
  )
}

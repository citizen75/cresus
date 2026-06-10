import { useState, useEffect } from 'react'
import { useEnrichedPositions } from '@/hooks/useEnrichedPositions'
import { useHistoricalDataLoader } from '@/hooks/useHistoricalDataLoader'
import { PortfolioHoldingsTable } from './PortfolioHoldingsTable'
import CardChart from '@/components/CardChart'
import { ChartModal } from '@/components/ChartModal'
import { TradingDialog } from '@/components/TradingDialog'
import { getApiBaseUrl, api } from '@/services/api'

interface PortfolioHoldingsWidgetProps {
  portfolioName: string
  onClose?: () => void
  filterTickers?: string[] // Only show these tickers
  onGetHistoricalData?: (ticker: string, days: number) => Promise<any>
}

export default function PortfolioHoldingsWidget({
  portfolioName,
  onClose,
  filterTickers,
  onGetHistoricalData,
}: PortfolioHoldingsWidgetProps) {
  const [rawPositions, setRawPositions] = useState<any[]>([])
  const [isLoadingPositions, setIsLoadingPositions] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [sectorFilter, setSectorFilter] = useState('All sectors')
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null)
  const [chartModalTicker, setChartModalTicker] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'table' | 'charts' | 'history'>('table')
  const [transactions, setTransactions] = useState<any[]>([])
  const [loadingTransactions, setLoadingTransactions] = useState(false)
  const [timeframe, setTimeframe] = useState<'1W' | '1M' | '3M' | 'YTD' | 'ALL'>('1M')
  const [tradingDialogOpen, setTradingDialogOpen] = useState(false)
  const [tradingMode, setTradingMode] = useState<'buy' | 'sell'>('buy')
  const [tradingTicker, setTradingTicker] = useState<string | null>(null)
  const [tradingPosition, setTradingPosition] = useState<any>(null)

  // Use centralized data loader
  const { historicalData, loadData, setHistoricalData } = useHistoricalDataLoader()

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

  // Load historical data for charts (use centralized hook)
  useEffect(() => {
    if (viewMode === 'charts' && filteredPositions && filteredPositions.length > 0 && Object.keys(historicalData).length === 0) {
      const tickers = filteredPositions.map((pos: any) => pos.ticker)
      const fetchFn = onGetHistoricalData || api.getHistoricalData.bind(api)
      console.log(`[PortfolioHoldingsWidget] Loading data for ${tickers.length} positions`)
      loadData(tickers, fetchFn).then(loaded => {
        if (loaded) setHistoricalData(loaded)
      })
    }
  }, [viewMode, filteredPositions, historicalData, onGetHistoricalData, loadData, setHistoricalData])

  // Transform raw API data to chart format
  const transformHistoricalData = (rawData: any[]): any[] => {
    if (!rawData || rawData.length === 0) return []

    return rawData
      .map((item: any) => ({
        date: item.date || item.timestamp || item.Date,
        close: parseFloat(item.close || item.Close || 0),
        open: parseFloat(item.open || item.Open || 0),
        high: parseFloat(item.high || item.High || 0),
        low: parseFloat(item.low || item.Low || 0),
        volume: parseFloat(item.volume || item.Volume || 0),
      }))
      .sort((a: any, b: any) => {
        const dateA = new Date(a.date)
        const dateB = new Date(b.date)
        return dateA.getTime() - dateB.getTime()
      })
  }

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

  const handleBuy = (ticker: string, position: any) => {
    setTradingTicker(ticker)
    setTradingPosition(position)
    setTradingMode('buy')
    setTradingDialogOpen(true)
  }

  const handleSell = (ticker: string, position: any) => {
    setTradingTicker(ticker)
    setTradingPosition(position)
    setTradingMode('sell')
    setTradingDialogOpen(true)
  }

  const handleTradingConfirm = (quantity: number, price?: number) => {
    console.log(`${tradingMode.toUpperCase()} ${quantity} shares of ${tradingTicker} at ${price || 'market'} price`)
    alert(`${tradingMode === 'buy' ? 'Buy' : 'Sell'} order created:\n${quantity} shares of ${tradingTicker}`)
    setTradingDialogOpen(false)
  }

  // Load transaction history
  useEffect(() => {
    if (viewMode === 'history') {
      loadTransactionHistory()
    }
  }, [viewMode])

  const loadTransactionHistory = async () => {
    try {
      setLoadingTransactions(true)
      const baseUrl = getApiBaseUrl()
      const response = await fetch(`${baseUrl}/api/v1/portfolios/${portfolioName}/transactions`)
      if (response.ok) {
        const data = await response.json()
        const txs = Array.isArray(data) ? data : data.transactions || []
        console.log('[PortfolioHoldingsWidget] Transaction sample:', txs[0])
        setTransactions(txs)
      }
    } catch (err) {
      console.error('Failed to load transactions:', err)
      setTransactions([])
    } finally {
      setLoadingTransactions(false)
    }
  }

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
          <button
            onClick={() => setViewMode('history')}
            className={`px-2 py-1 rounded text-xs font-medium transition ${
              viewMode === 'history'
                ? 'bg-purple-600 text-white'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            📜 History
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
        {!isLoading && viewMode === 'table' && (
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
            onBuy={handleBuy}
            onSell={handleSell}
            showSearch={false}
            showActions={true}
            externalSearchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
            showViewToggle={false}
          />
        )}

        {!isLoading && viewMode === 'charts' && (
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
                  {(() => {
                    const rawData = historicalData[pos.ticker] || []
                    const transformedData = transformHistoricalData(rawData)
                    const chartData = filterDataByTimeframe(transformedData, timeframe)
                    return chartData && chartData.length > 0 ? (
                      <CardChart
                        data={chartData}
                        ticker={pos.ticker}
                        showVariation={false}
                      />
                    ) : (
                      <div className="p-4 h-32 bg-slate-700/20 flex items-center justify-center gap-2">
                        <p className="text-slate-500 text-xs">No chart data</p>
                      </div>
                    )
                  })()}

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

        {!isLoading && viewMode === 'history' && (
          <div className="overflow-auto h-full">
            {loadingTransactions ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-slate-400">Loading transactions...</p>
              </div>
            ) : transactions.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-slate-400">No transactions yet</p>
              </div>
            ) : (
              <table className="w-full text-xs">
                <thead className="bg-slate-800/50 sticky top-0">
                  <tr>
                    <th className="px-3 py-2 text-left text-slate-300">Date</th>
                    <th className="px-3 py-2 text-left text-slate-300">Ticker</th>
                    <th className="px-3 py-2 text-left text-slate-300">Name</th>
                    <th className="px-3 py-2 text-center text-slate-300">Type</th>
                    <th className="px-3 py-2 text-right text-slate-300">Qty</th>
                    <th className="px-3 py-2 text-right text-slate-300">Price</th>
                    <th className="px-3 py-2 text-right text-slate-300">Fees</th>
                    <th className="px-3 py-2 text-right text-slate-300">Stop Loss</th>
                    <th className="px-3 py-2 text-right text-slate-300">Target</th>
                    <th className="px-3 py-2 text-right text-slate-300">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {transactions.map((tx: any, idx: number) => {
                    // Parse date - try different field names
                    let dateStr = '—'
                    try {
                      const dateValue = tx.date || tx.timestamp || tx.Date || tx.Timestamp || tx.entry_date || tx.created_at
                      if (dateValue) {
                        const dateObj = new Date(dateValue)
                        if (!isNaN(dateObj.getTime())) {
                          dateStr = dateObj.toLocaleDateString('en-US', { year: '2-digit', month: '2-digit', day: '2-digit' })
                        }
                      }
                    } catch (e) {
                      console.log('[PortfolioHoldingsWidget] Date parse error for tx:', tx, e)
                    }

                    return (
                      <tr key={idx} className="hover:bg-slate-800/30">
                        <td className="px-3 py-2 text-slate-300">{dateStr}</td>
                        <td className="px-3 py-2 font-medium text-white">{tx.ticker}</td>
                        <td className="px-3 py-2 text-slate-400">{tx.name || tx.company_name || '—'}</td>
                        <td className="px-3 py-2 text-center">
                          {(() => {
                            // Try different field names for transaction type
                            const type = tx.type || tx.side || tx.action || tx.direction || tx.operation || tx.Type || tx.Side
                            const isBuy = type?.toLowerCase() === 'buy' || type?.toLowerCase() === 'long'

                            return (
                              <span className={`px-2 py-1 rounded text-xs font-medium ${
                                isBuy
                                  ? 'bg-green-900/30 text-green-300'
                                  : 'bg-red-900/30 text-red-300'
                              }`}>
                                {type || '—'}
                              </span>
                            )
                          })()}
                        </td>
                        <td className="px-3 py-2 text-right text-slate-300">{tx.quantity}</td>
                        <td className="px-3 py-2 text-right text-slate-300">€{parseFloat(tx.price || 0).toFixed(2)}</td>
                        <td className="px-3 py-2 text-right text-slate-300">€{parseFloat(tx.fees || 0).toFixed(2)}</td>
                        <td className="px-3 py-2 text-right text-slate-300">{tx.stop_loss ? `€${parseFloat(tx.stop_loss).toFixed(2)}` : '—'}</td>
                        <td className="px-3 py-2 text-right text-slate-300">{tx.target_profit ? `€${parseFloat(tx.target_profit).toFixed(2)}` : '—'}</td>
                        <td className="px-3 py-2 text-right text-white font-medium">
                          €{((tx.quantity * parseFloat(tx.price || 0)) - parseFloat(tx.fees || 0)).toFixed(2)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
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

      {/* Trading Dialog */}
      <TradingDialog
        isOpen={tradingDialogOpen}
        mode={tradingMode}
        ticker={tradingTicker || ''}
        position={tradingPosition}
        currentPrice={tradingPosition?.current_price || 0}
        onClose={() => setTradingDialogOpen(false)}
        onConfirm={handleTradingConfirm}
      />
    </div>
  )
}

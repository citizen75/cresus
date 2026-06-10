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
  const [timeframe, setTimeframe] = useState<'1W' | '1M' | '3M' | 'YTD' | 'ALL'>('1M')
  const [tradingDialogOpen, setTradingDialogOpen] = useState(false)
  const [tradingMode, setTradingMode] = useState<'buy' | 'sell'>('buy')
  const [tradingTicker, setTradingTicker] = useState<string | null>(null)
  const [tradingPosition, setTradingPosition] = useState<any>(null)

  // Transaction history state
  const [transactions, setTransactions] = useState<any[]>([])
  const [loadingTransactions, setLoadingTransactions] = useState(false)

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

  // Use centralized data loader
  const { historicalData, loadData, setHistoricalData } = useHistoricalDataLoader()

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

  // Load transaction history when history view is opened
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
        setTransactions(Array.isArray(data) ? data : data.transactions || [])
      }
    } catch (err) {
      console.error('Failed to load transactions:', err)
      setTransactions([])
    } finally {
      setLoadingTransactions(false)
    }
  }

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

    return data
      .filter((item: any) => {
        const itemDate = new Date(item.date || item.timestamp)
        return itemDate >= cutoffDate
      })
      .sort((a: any, b: any) => {
        const dateA = new Date(a.date || a.timestamp)
        const dateB = new Date(b.date || b.timestamp)
        return dateB.getTime() - dateA.getTime()
      })
  }

  const handleBuyClick = (pos: any) => {
    setTradingPosition(pos)
    setTradingTicker(pos.ticker)
    setTradingMode('buy')
    setTradingDialogOpen(true)
  }

  const handleSellClick = (pos: any) => {
    setTradingPosition(pos)
    setTradingTicker(pos.ticker)
    setTradingMode('sell')
    setTradingDialogOpen(true)
  }

  if (!portfolioName) {
    return (
      <div className="p-4 text-slate-400">
        No portfolio selected
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-slate-950 text-white">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-slate-800 bg-slate-900/50 px-6 py-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <h2 className="text-xl font-bold">{portfolioName.toUpperCase()} Holdings</h2>

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

          {/* View Toggle */}
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
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden relative">
        {isLoading && (
          <div className="absolute inset-0 bg-slate-900/50 rounded flex items-center justify-center z-10">
            <div className="text-center">
              <div className="inline-block">
                <div className="w-12 h-12 border-4 border-slate-700 border-t-purple-600 rounded-full animate-spin"></div>
              </div>
            </div>
          </div>
        )}

        {/* Table View */}
        {viewMode === 'table' && (
          <div className="overflow-auto h-full">
            {filteredPositions.length === 0 ? (
              <div className="p-6 text-center text-slate-400">
                No positions in this portfolio
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-6 auto-rows-max">
                {filteredPositions.map((pos: any) => (
                  <div
                    key={pos.ticker}
                    className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden flex flex-col"
                  >
                    {/* Card Header */}
                    <div className="border-b border-slate-700 p-4 bg-slate-900/30">
                      <div className="font-bold text-white text-lg">{pos.ticker}</div>
                      <div className="text-xs text-slate-400">{pos.company_name || pos.sector || 'N/A'}</div>
                      <div className="text-xs text-slate-500 mt-1">
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
                      <div className="flex gap-2 mt-3">
                        <button
                          onClick={() => handleBuyClick(pos)}
                          className="flex-1 px-2 py-1 bg-green-900/30 hover:bg-green-900/50 text-green-300 rounded text-xs font-medium transition"
                        >
                          💰 Buy
                        </button>
                        <button
                          onClick={() => handleSellClick(pos)}
                          className="flex-1 px-2 py-1 bg-red-900/30 hover:bg-red-900/50 text-red-300 rounded text-xs font-medium transition"
                        >
                          📊 Sell
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Charts View */}
        {viewMode === 'charts' && (
          <div className="overflow-auto h-full">
            {filteredPositions.length === 0 ? (
              <div className="p-6 text-center text-slate-400">
                No positions in this portfolio
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6 auto-rows-max">
                {filteredPositions.map((pos: any) => (
                  <div
                    key={pos.ticker}
                    className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden"
                  >
                    <div className="border-b border-slate-700 p-4 bg-slate-900/30 flex justify-between items-start">
                      <div>
                        <div className="font-bold text-white">{pos.ticker}</div>
                        <div className="text-xs text-slate-400">{pos.company_name || 'N/A'}</div>
                      </div>
                      <button
                        onClick={() => setChartModalTicker(pos.ticker)}
                        className="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded transition"
                      >
                        ↗️ Expand
                      </button>
                    </div>
                    {(() => {
                      const rawData = historicalData[pos.ticker] || []
                      const transformedData = transformHistoricalData(rawData)
                      const chartData = filterDataByTimeframe(transformedData, timeframe)
                      return chartData && chartData.length > 0 ? (
                        <CardChart
                          data={chartData}
                          ticker={pos.ticker}
                        />
                      ) : (
                        <div className="p-4 h-48 bg-slate-700/20 flex items-center justify-center">
                          <p className="text-slate-500 text-xs">No data available</p>
                        </div>
                      )
                    })()}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* History View */}
        {viewMode === 'history' && (
          <div className="overflow-auto h-full">
            {loadingTransactions ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-slate-400">Loading transactions...</div>
              </div>
            ) : transactions.length === 0 ? (
              <div className="p-6 text-center text-slate-400">
                No transactions yet
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-800/50 sticky top-0">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-300">Date</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-300">Ticker</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-300">Type</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-slate-300">Quantity</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-slate-300">Price</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-slate-300">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {transactions.map((tx: any, idx: number) => (
                      <tr key={idx} className="hover:bg-slate-800/30 transition">
                        <td className="px-6 py-3 text-sm text-slate-300">
                          {new Date(tx.date || tx.timestamp).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-3 text-sm font-medium text-white">{tx.ticker}</td>
                        <td className="px-6 py-3 text-sm">
                          <span
                            className={`px-2 py-1 rounded text-xs font-medium ${
                              tx.type?.toLowerCase() === 'buy'
                                ? 'bg-green-900/30 text-green-300'
                                : 'bg-red-900/30 text-red-300'
                            }`}
                          >
                            {tx.type}
                          </span>
                        </td>
                        <td className="px-6 py-3 text-sm text-right text-slate-300">
                          {tx.quantity}
                        </td>
                        <td className="px-6 py-3 text-sm text-right text-slate-300">
                          €{parseFloat(tx.price || 0).toFixed(2)}
                        </td>
                        <td className="px-6 py-3 text-sm text-right text-white font-medium">
                          €{(tx.quantity * parseFloat(tx.price || 0)).toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
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
        onClose={() => {
          setTradingDialogOpen(false)
          setTradingTicker(null)
          setTradingPosition(null)
        }}
        onConfirm={(quantity, price) => {
          const action = tradingMode === 'buy' ? 'Buy' : 'Sell'
          alert(`${action} order created:\n${quantity} shares of ${tradingTicker}`)
          setTradingDialogOpen(false)
          setTradingTicker(null)
          setTradingPosition(null)
        }}
      />
    </div>
  )
}

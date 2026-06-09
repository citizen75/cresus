import { useState, useCallback, useEffect } from 'react'
import GlobalConversationPanel from '@/components/portfolio/GlobalConversationPanel'
import TradingChart from '@/components/TradingChart'
import CardChart from '@/components/CardChart'
import { PortfolioHoldingsTable } from '@/components/portfolio/PortfolioHoldingsTable'
import { api } from '@/services/api'

interface AlertInfo {
  title: string
  portfolio?: string
  tickers: string[]
  content: string
}

export default function Dashboard() {
  const [conversationOpen, setConversationOpen] = useState(true)
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
  const [chartHistory, setChartHistory] = useState<string[]>([])
  const [alertGridView, setAlertGridView] = useState<AlertInfo | null>(null)
  const [historicalData, setHistoricalData] = useState<Record<string, any[]>>({})
  const [viewMode, setViewMode] = useState<'table' | 'charts'>('table')
  const [timeframe, setTimeframe] = useState<'1W' | '1M' | '3M' | 'YTD' | 'ALL'>('1M')
  const [portfolioPositions, setPortfolioPositions] = useState<any[]>([])

  const handleSelectTicker = useCallback((ticker: string) => {
    setSelectedTicker(ticker)
    setAlertGridView(null) // Close grid view when selecting a single ticker
    // Add to history if not already there, keep last 10
    setChartHistory((prev) => {
      const filtered = prev.filter((t) => t !== ticker)
      return [ticker, ...filtered].slice(0, 10)
    })
  }, [])

  const handleAlertGridClick = useCallback((alertInfo: AlertInfo) => {
    setAlertGridView(alertInfo)
    setSelectedTicker(null) // Close single chart when opening grid
  }, [])

  const filterDataByTimeframe = (data: any[], tf: string) => {
    if (tf === 'ALL' || !data || data.length === 0) return data

    let cutoffDate = new Date()

    if (tf === 'YTD') {
      // Year To Date: from Jan 1 to today
      cutoffDate = new Date(cutoffDate.getFullYear(), 0, 1)
    } else {
      // Other periods: N days back from today
      const days =
        tf === '1W' ? 7 : tf === '1M' ? 30 : tf === '3M' ? 90 : 365
      cutoffDate.setDate(cutoffDate.getDate() - days)
    }

    return data.filter((item: any) => {
      const itemDate = new Date(item.date)
      return itemDate >= cutoffDate
    })
  }

  // Load portfolio positions when alert has a portfolio
  useEffect(() => {
    if (!alertGridView?.portfolio) {
      setPortfolioPositions([])
      return
    }

    const loadPositions = async () => {
      try {
        const response = await api.listPortfolios()
        const portfolio = response.portfolios?.find(
          (p: any) => p.name === alertGridView.portfolio
        )
        if (portfolio) {
          const positionResponse = await fetch(
            `/api/v1/portfolios/${encodeURIComponent(alertGridView.portfolio || '')}/positions`
          )
          if (positionResponse.ok) {
            const data = await positionResponse.json()
            setPortfolioPositions(data.positions || [])
          }
        }
      } catch (err) {
        console.error('Failed to load portfolio positions:', err)
      }
    }

    loadPositions()
  }, [alertGridView?.portfolio])

  // Load historical data when grid view is activated
  useEffect(() => {
    if (!alertGridView || alertGridView.tickers.length === 0) return

    const loadData = async () => {
      const data: Record<string, any[]> = {}
      for (const ticker of alertGridView.tickers) {
        try {
          const result = await api.getHistoricalData(ticker, 1825) // ~5 years
          let historyArray = []
          if (result && Array.isArray(result)) {
            historyArray = result
          } else if (result && result.history && Array.isArray(result.history)) {
            historyArray = result.history
          } else if (result && result.data && Array.isArray(result.data)) {
            historyArray = result.data
          }
          if (historyArray.length > 0) {
            data[ticker] = historyArray.map((item: any) => ({
              date: item.date || item.timestamp || item.Date,
              close: parseFloat(item.close || item.Close),
            }))
          }
        } catch (err) {
          console.error(`Failed to load data for ${ticker}:`, err)
        }
      }
      setHistoricalData(data)
    }

    loadData()
  }, [alertGridView])

  return (
    <div className="flex gap-6 h-[calc(100vh-120px)]">
      {/* Center Column - Conversations */}
      {conversationOpen && (
        <div className="w-[500px] flex-shrink-0">
          <GlobalConversationPanel
            onClose={() => setConversationOpen(false)}
            onAlertClick={handleSelectTicker}
            onAlertGridClick={handleAlertGridClick}
          />
        </div>
      )}

      {/* Right Column - Chart or Grid */}
      <div className="flex-1 flex flex-col bg-slate-900 rounded-lg border border-slate-800">
        {/* Header */}
        <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">{alertGridView ? '📊' : '📈'}</span>
            <div>
              <h3 className="text-sm font-semibold text-white">
                {alertGridView ? alertGridView.title : selectedTicker ? selectedTicker : 'Chart'}
              </h3>
              {alertGridView?.portfolio && (
                <p className="text-xs text-slate-400">Portfolio: {alertGridView.portfolio}</p>
              )}
            </div>
          </div>
          {(selectedTicker || alertGridView) && (
            <button
              onClick={() => {
                setSelectedTicker(null)
                setAlertGridView(null)
              }}
              className="text-slate-500 hover:text-slate-400"
            >
              ✕
            </button>
          )}
        </div>

        {/* Tabs and Controls - Show when alert grid is open */}
        {alertGridView && (
          <>
            {/* Tab Navigation */}
            <div className="border-b border-slate-800">
              <div className="flex gap-8 px-4">
                {(['table', 'charts'] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setViewMode(mode)}
                    className={`px-1 py-3 font-medium text-sm transition border-b-2 ${
                      viewMode === mode
                        ? 'border-purple-600 text-white'
                        : 'border-transparent text-slate-400 hover:text-slate-300'
                    }`}
                  >
                    {mode === 'table' ? 'Table' : 'Charts'}
                  </button>
                ))}
              </div>
            </div>

            {/* Timeframe Selector - Show in both modes */}
            <div className="border-b border-slate-800 bg-slate-950 px-4 py-3">
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold text-slate-400">Period:</span>
                <div className="flex gap-2">
                  {(['1W', '1M', '3M', 'YTD', 'ALL'] as const).map((tf) => (
                    <button
                      key={tf}
                      onClick={() => setTimeframe(tf)}
                      className={`px-3 py-1 rounded text-xs font-medium transition ${
                        timeframe === tf
                          ? 'bg-purple-600 text-white'
                          : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      {tf}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}

        {/* Chart History */}
        {chartHistory.length > 0 && !alertGridView && (
          <div className="border-b border-slate-800 bg-slate-950 px-4 py-3">
            <div className="text-xs font-semibold text-slate-400 mb-2">History</div>
            <div className="flex gap-2 overflow-x-auto pb-2">
              {chartHistory.map((ticker) => (
                <button
                  key={ticker}
                  onClick={() => handleSelectTicker(ticker)}
                  className={`px-3 py-1 rounded text-sm font-medium whitespace-nowrap transition-colors ${
                    selectedTicker === ticker
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {ticker}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-hidden p-4">
          {alertGridView ? (
            // Alert View - Table or Charts
            viewMode === 'table' ? (
              <div className="h-full overflow-auto p-4">
                {alertGridView.portfolio && portfolioPositions.length > 0 ? (
                  <PortfolioHoldingsTable
                    positions={portfolioPositions}
                    totalValue={portfolioPositions.reduce((sum: number, p: any) => sum + (p.position_value || 0), 0)}
                    currency="EUR"
                    filterTickers={alertGridView.tickers}
                    showSearch={true}
                    showActions={true}
                    onSelectPosition={(ticker) => handleSelectTicker(ticker)}
                  />
                ) : (
                  <PortfolioHoldingsTable
                    positions={alertGridView.tickers.map((ticker) => {
                      const tickerData = historicalData[ticker]
                      const filteredData = filterDataByTimeframe(tickerData || [], timeframe)
                      const firstPrice = filteredData?.[0]?.close
                      const lastPrice = filteredData?.[filteredData.length - 1]?.close
                      const change =
                        firstPrice && lastPrice
                          ? ((lastPrice - firstPrice) / firstPrice) * 100
                          : 0

                      return {
                        ticker,
                        company_name: '',
                        quantity: 1,
                        avg_entry_price: firstPrice || 0,
                        current_price: lastPrice || 0,
                        position_value: lastPrice || 0,
                        position_gain: (lastPrice || 0) - (firstPrice || 0),
                        position_gain_pct: change,
                      }
                    })}
                    totalValue={alertGridView.tickers.length}
                    currency="EUR"
                    showSearch={true}
                    showActions={true}
                    onSelectPosition={(ticker) => handleSelectTicker(ticker)}
                  />
                )}
              </div>
            ) : (
              // Grid View - All Tickers (Same layout as HoldingsView)
            <div className="h-full overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {alertGridView.tickers.map((ticker) => {
                  const tickerData = historicalData[ticker]
                  const filteredData = filterDataByTimeframe(tickerData || [], timeframe)
                  const change = (() => {
                    if (!filteredData || filteredData.length < 2) return 0
                    const firstPrice = filteredData[0]?.close
                    const lastPrice = filteredData[filteredData.length - 1]?.close
                    return firstPrice ? ((lastPrice - firstPrice) / firstPrice) * 100 : 0
                  })()

                  return (
                    <div
                      key={ticker}
                      className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden hover:border-purple-600/50 transition cursor-pointer"
                      onClick={() => handleSelectTicker(ticker)}
                    >
                      {/* Card Header */}
                      <div className="bg-slate-800/50 border-b border-slate-800 p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <p className="text-white font-bold text-lg">{ticker}</p>
                            <p className="text-slate-400 text-xs">Alert Ticker</p>
                          </div>
                          <div className="text-right">
                            <p className={`text-2xl font-bold ${change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              {change.toFixed(1)}%
                            </p>
                            <p className="text-slate-400 text-xs">Change</p>
                          </div>
                        </div>
                      </div>

                      {/* Chart */}
                      {filteredData && filteredData.length > 0 ? (
                        <CardChart
                          data={filteredData}
                          ticker={ticker}
                          showVariation={false}
                        />
                      ) : (
                        <div className="p-4 h-48 bg-slate-800/20 flex flex-col items-center justify-center gap-2">
                          <p className="text-slate-500 text-sm">Loading chart...</p>
                        </div>
                      )}

                      {/* Price Range Row */}
                      {filteredData && filteredData.length > 0 && (() => {
                        const lastPrice = filteredData[filteredData.length - 1]?.close
                        const minPrice = Math.min(...filteredData.map((d: any) => d.close))
                        const maxPrice = Math.max(...filteredData.map((d: any) => d.close))
                        return (
                          <div className="border-t border-slate-800 px-4 py-3 bg-slate-800/30">
                            <div className="flex justify-between items-center text-xs">
                              <div className="flex flex-col items-center flex-1">
                                <p className="text-slate-500 text-xs mb-1">Low</p>
                                <p className="text-white font-medium">€{minPrice?.toFixed(3)}</p>
                              </div>
                              <div className="flex flex-col items-center flex-1">
                                <p className="text-slate-500 text-xs mb-1">Current</p>
                                <p className={`font-medium ${change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                  €{lastPrice?.toFixed(2)}
                                </p>
                              </div>
                              <div className="flex flex-col items-center flex-1">
                                <p className="text-slate-500 text-xs mb-1">High</p>
                                <p className="text-white font-medium">€{maxPrice?.toFixed(3)}</p>
                              </div>
                            </div>
                          </div>
                        )
                      })()}

                      {/* Card Footer */}
                      <div className="border-t border-slate-800 p-4 text-center">
                        <p className="text-xs text-slate-400">Click to expand chart</p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
            )
          ) : selectedTicker ? (
            // Single Chart View
            <TradingChart ticker={selectedTicker} timeframe={timeframe} />
          ) : (
            // Empty State
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-slate-500">
                <div className="text-4xl mb-2">📌</div>
                <div className="text-xs">Click on an alert to view chart</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

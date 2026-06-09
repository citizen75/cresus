import { useState, useCallback, useEffect, useRef } from 'react'
import { ConversationWidget } from '@/components/ConversationWidget'
import TradingChart from '@/components/TradingChart'
import CardChart from '@/components/CardChart'
import { PortfolioHoldingsTable } from '@/components/portfolio/PortfolioHoldingsTable'
import PortfolioHoldingsWidget from '@/components/portfolio/PortfolioHoldingsWidget'
import { ChartModal } from '@/components/ChartModal'
import { api, getApiBaseUrl } from '@/services/api'

interface AlertInfo {
  title: string
  portfolio?: string
  tickers: string[]
  content: string
}

export default function Dashboard() {
  const conversationPanelRef = useRef<{ scrollToBottom: () => void } | null>(null)
  const [conversationOpen, setConversationOpen] = useState(true)
  const [rightPanelOpen, setRightPanelOpen] = useState(false)
  const [chartModalTicker, setChartModalTicker] = useState<string | null>(null)
  const [chartHistory, setChartHistory] = useState<string[]>([])
  const [alertHistory, setAlertHistory] = useState<{ id: string; info: AlertInfo }[]>([])
  const [alertGridView, setAlertGridView] = useState<AlertInfo | null>(null)
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null)
  const [selectedTableTicker, setSelectedTableTicker] = useState<string | null>(null)
  const [historicalData, setHistoricalData] = useState<Record<string, any[]>>({})
  const [tickerInfo, setTickerInfo] = useState<Record<string, any>>({})
  const [fundamentalData, setFundamentalData] = useState<Record<string, any>>({})
  const [viewMode, setViewMode] = useState<'table' | 'charts'>('table')
  const [timeframe, setTimeframe] = useState<'1W' | '1M' | '3M' | 'YTD' | 'ALL'>('1M')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [portfolioPositions, setPortfolioPositions] = useState<any[]>([])
  const [fundamentalCache, setFundamentalCache] = useState<Record<string, any>>({})

  // Fetch and auto-select most recent alert on mount
  useEffect(() => {
    const loadMostRecentAlert = async () => {
      try {
        const baseUrl = getApiBaseUrl()
        const response = await fetch(`${baseUrl}/api/v1/conversations/_global`)
        if (!response.ok) return

        const data = await response.json()
        const messages = data.history || []

        // Find the most recent alert message
        for (let i = messages.length - 1; i >= 0; i--) {
          const msg = messages[i]
          if (msg.source === 'alert') {
            // Parse alert content
            const lines = msg.content.split('\n')
            const alertInfo: AlertInfo = {
              title: '',
              portfolio: undefined,
              tickers: [],
              content: msg.content,
            }

            for (const line of lines) {
              if (line.startsWith('**Portfolio:**')) {
                alertInfo.portfolio = line.replace('**Portfolio:**', '').trim()
              }
              if (line.includes('🚨') || line.includes('⚠️')) {
                const match = line.match(/\*\*([^*]+)\*\*/)
                if (match) {
                  alertInfo.title = match[1]
                }
              }
              if (line.startsWith('  •')) {
                const match = line.match(/•\s+([A-Z0-9.-]+):/)
                if (match) {
                  alertInfo.tickers.push(match[1])
                }
              }
            }

            if (alertInfo.tickers.length > 0) {
              const alertId = `${i}-${msg.datetime}`
              console.log(`[Dashboard] Parsed alert: portfolio="${alertInfo.portfolio}", tickers=${alertInfo.tickers.length}`)
              setAlertGridView(alertInfo)
              setSelectedAlertId(alertId)
              setAlertHistory([{ id: alertId, info: alertInfo }])
              setRightPanelOpen(true)
              setTimeout(() => {
                conversationPanelRef.current?.scrollToBottom()
              }, 100)
              break
            }
          }
        }
      } catch (err) {
        console.error('Failed to load most recent alert:', err)
      }
    }

    loadMostRecentAlert()
  }, [])

  const handleSelectTicker = useCallback((ticker: string) => {
    setChartModalTicker(ticker)
    setSelectedTableTicker(ticker)
    // Add to history if not already there, keep last 10
    setChartHistory((prev) => {
      const filtered = prev.filter((t) => t !== ticker)
      return [ticker, ...filtered].slice(0, 10)
    })
  }, [])

  const handleAlertGridClick = useCallback((alertInfo: AlertInfo, alertId?: string) => {
    setAlertGridView(alertInfo)
    setRightPanelOpen(true)
    setSelectedAlertId(alertId || null)
    setSelectedTableTicker(null)

    // Add to alert history (keep last 10)
    if (alertId) {
      setAlertHistory((prev) => {
        const filtered = prev.filter((a) => a.id !== alertId)
        return [{ id: alertId, info: alertInfo }, ...filtered].slice(0, 10)
      })
    }
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

  // Auto-select most recent alert when none is selected
  useEffect(() => {
    if (!alertGridView && alertHistory.length > 0) {
      const mostRecentAlert = alertHistory[0]
      setAlertGridView(mostRecentAlert.info)
      setSelectedAlertId(mostRecentAlert.id)
      setRightPanelOpen(true)
      // Scroll conversation to bottom
      setTimeout(() => {
        conversationPanelRef.current?.scrollToBottom()
      }, 0)
    }
  }, [alertHistory])

  // Load portfolio positions and their fundamental data when alert has a portfolio
  useEffect(() => {
    console.log(`[Dashboard] Portfolio effect: alertGridView?.portfolio="${alertGridView?.portfolio}"`)
    if (!alertGridView?.portfolio) {
      setPortfolioPositions([])
      return
    }

    const loadPositionsAndFundamental = async () => {
      console.log(`[Dashboard] Loading positions for portfolio: ${alertGridView.portfolio}`)
      try {
        const response = await api.listPortfolios()
        const portfolio = response.portfolios?.find(
          (p: any) => p.name === alertGridView.portfolio
        )
        if (portfolio) {
          const baseUrl = getApiBaseUrl()
          const positionResponse = await fetch(
            `${baseUrl}/api/v1/portfolios/${encodeURIComponent(alertGridView.portfolio || '')}/positions`
          )
          if (positionResponse.ok) {
            const data = await positionResponse.json()
            let positions = data.positions || []
            console.log(`[Dashboard] Loaded portfolio ${alertGridView.portfolio}: ${positions.length} positions`)

            // Fetch fundamental data for portfolio positions (using cache)
            const fundData: Record<string, any> = { ...fundamentalCache }
            for (const pos of positions) {
              // Skip if already cached
              if (fundData[pos.ticker]) {
                console.log(`[Dashboard] Using cached fundamental data for ${pos.ticker}`)
                continue
              }
              try {
                const result = await api.getFundamental(pos.ticker)
                fundData[pos.ticker] = result?.data?.quotation || {}
              } catch (err) {
                console.error(`Failed to load fundamental data for ${pos.ticker}:`, err)
                fundData[pos.ticker] = {}
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

              console.log(`[Dashboard] ✓ ${pos.ticker}: current=${currentPrice}, prev=${previousClose}, daily=${dailyChange} (${dailyChangePct}%)`)

              return {
                ...pos,
                position_gain: dailyChange,  // Daily change per share
                position_gain_pct: dailyChangePct,
                asset_type: fund.asset_type || 'Stock',
                sector: fund.sector || 'Unknown',
              }
            })

            setPortfolioPositions(positions)
            setFundamentalData(fundData)
          }
        }
      } catch (err) {
        console.error('Failed to load portfolio positions:', err)
      }
    }

    loadPositionsAndFundamental()
  }, [alertGridView?.portfolio])

  // Load historical data, ticker info and fundamental data when grid view is activated
  useEffect(() => {
    if (!alertGridView || alertGridView.tickers.length === 0) return

    const loadData = async () => {
      console.log(`[Dashboard] Loading data for alert: ${alertGridView.title}, tickers:`, alertGridView.tickers)
      const data: Record<string, any[]> = {}
      const info: Record<string, any> = {}
      const fundamental: Record<string, any> = {}

      for (const ticker of alertGridView.tickers) {
        try {
          // Initialize variables
          let companyName = ticker
          let sector = 'Unknown'
          let currentPrice = 0
          let previousClose = 0

          // Load historical data
          const result = await api.getHistoricalData(ticker, 1825) // ~5 years
          let historyArray = []
          if (result && Array.isArray(result)) {
            historyArray = result
          } else if (result && result.history && Array.isArray(result.history)) {
            historyArray = result.history
          } else if (result && result.data && Array.isArray(result.data)) {
            historyArray = result.data
          }
          console.log(`[Dashboard] ${ticker} history: ${historyArray.length} rows`)
          if (historyArray.length > 0) {
            data[ticker] = historyArray.map((item: any) => ({
              date: item.date || item.timestamp || item.Date,
              close: parseFloat(item.close || item.Close),
            }))
            // Get prices from historical data
            currentPrice = parseFloat(historyArray[historyArray.length - 1]?.close || 0)
            previousClose = historyArray.length > 1 ? parseFloat(historyArray[historyArray.length - 2]?.close || currentPrice) : currentPrice
            console.log(`[Dashboard] ${ticker}: currentPrice=${currentPrice}, previousClose=${previousClose}`)
          }

          // Fetch fundamental data for company info and prices (using cache)
          let fundData = { data: {} }
          let fundResponse: any = null
          if (fundamentalCache[ticker]?.current_price) {
            console.log(`[Dashboard] Using cached fundamental data for ${ticker}`)
            fundData = { data: { quotation: fundamentalCache[ticker] } }
          } else {
            const baseUrl = getApiBaseUrl()
            fundResponse = await fetch(`${baseUrl}/api/v1/data/fundamental/${ticker}`)
            fundData = await fundResponse.json()
            console.log(`[Dashboard] ${ticker} fundResponse.ok=${fundResponse.ok}, has quotation=${!!fundData?.data?.quotation}`)
            // Cache the result
            if (fundData?.data?.quotation) {
              setFundamentalCache((prev) => ({
                ...prev,
                [ticker]: fundData.data.quotation,
              }))
            }
          }

          // Use fundamental data if available
          if (fundResponse?.ok && fundData?.data?.company?.name) {
            companyName = fundData.data.company.name
            sector = fundData.data.company.sector || 'Unknown'
          }

          // Use quotation data from fundamental endpoint if available
          if (fundResponse?.ok && fundData?.data?.quotation) {
            const api_current = fundData.data.quotation.current_price
            const api_previous = fundData.data.quotation.previous_close
            console.log(`[Dashboard] ${ticker} API: current=${api_current}, previous=${api_previous}`)
            currentPrice = api_current || currentPrice
            previousClose = api_previous || previousClose
          }

          info[ticker] = { company_name: companyName }
          fundamental[ticker] = {
            company_name: companyName,
            current_price: currentPrice,
            previous_close: previousClose,
            sector: sector,
          }
          console.log(`[Dashboard] ✓ ${ticker}: previous_close=${previousClose}`)
        } catch (err) {
          console.error(`[Dashboard] ✗ Failed to load data for ${ticker}:`, err)
          info[ticker] = { company_name: ticker }
          fundamental[ticker] = { company_name: ticker, current_price: 0, previous_close: 0, sector: 'Unknown' }
        }
      }
      setHistoricalData(data)
      setTickerInfo(info)
      console.log(`[Dashboard] Setting fundamental data:`, fundamental)
      setFundamentalData(fundamental)
    }

    loadData()
  }, [alertGridView])

  return (
    <div className="flex gap-6 h-[calc(100vh-120px)]">
      {/* Center Column - Conversations */}
      {conversationOpen && (
        <div className="w-[500px] flex-shrink-0 flex flex-col">
          <ConversationWidget
            portfolioName="_global"
            title="Global Chat"
            subtitle="All portfolios & alerts"
            maxHeight="h-full"
            onNewMessage={(msg) => {
              // Update recent alerts when new message arrives
              if (msg.source === 'alert') {
                // Parse alert content
                const lines = msg.content?.split('\n') || []
                const alertInfo: AlertInfo = {
                  title: '',
                  portfolio: msg.portfolio,
                  tickers: [],
                  content: msg.content || '',
                }

                for (const line of lines) {
                  if (line.startsWith('**Portfolio:**') && !alertInfo.portfolio) {
                    alertInfo.portfolio = line.replace('**Portfolio:**', '').trim()
                  }
                  if ((line.includes('🚨') || line.includes('⚠️')) && line.includes('**')) {
                    const match = line.match(/\*\*([^*]+)\*\*/)
                    if (match) {
                      alertInfo.title = match[1]
                    }
                  }
                  if (line.trim().startsWith('•')) {
                    const match = line.match(/•\s+([A-Z0-9.-]+):/)
                    if (match) {
                      alertInfo.tickers.push(match[1])
                    }
                  }
                }

                if (alertInfo.tickers.length > 0) {
                  const alertId = `${Date.now()}-${msg.datetime}`
                  setAlertHistory((prev) => [{ id: alertId, info: alertInfo }, ...prev].slice(0, 10))
                }
              }
            }}
            onPortfolioClick={(portfolio, tickers, widget) => {
              // Create alert info object and display holdings filtered by tickers
              const alertInfo: AlertInfo = {
                title: '',
                portfolio: portfolio,
                tickers: tickers,
                content: `Portfolio: ${portfolio}`,
              }
              setAlertGridView(alertInfo)
              setRightPanelOpen(true)
              // Widget data is available if message has widget field
              if (widget) {
                console.log('Message widget:', widget)
              }
            }}
            onSendMessage={async (message) => {
              const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
              const response = await fetch(`${baseUrl}/api/v1/conversations/_global/message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  source: 'user',
                  content: message,
                }),
              })
              if (!response.ok) throw new Error('Failed to send message')
            }}
          />
        </div>
      )}

      {/* Right Column - Portfolio Holdings Widget */}
      {rightPanelOpen && (
      <div className="flex-1 flex flex-col bg-slate-900 rounded-lg border border-slate-800 overflow-auto">
        {/* Recent Alerts & Charts */}
        {alertGridView && (alertHistory.length > 0 || chartHistory.length > 0) && (
          <div className="border-b border-slate-800 bg-slate-950 px-4 py-3 flex-shrink-0">
            <div className="text-xs font-semibold text-slate-400 mb-2">Recent</div>
            <div className="flex gap-2 overflow-x-auto pb-2">
              {/* Recent Alerts */}
              {alertHistory.map((alert) => (
                <button
                  key={alert.id}
                  onClick={() => handleAlertGridClick(alert.info, alert.id)}
                  className={`px-3 py-1 rounded text-sm font-medium whitespace-nowrap transition-colors flex-shrink-0 ${
                    selectedAlertId === alert.id
                      ? 'bg-red-600 text-white'
                      : 'bg-red-900/30 text-red-300 hover:bg-red-900/50'
                  }`}
                  title={`${alert.info.title}${alert.info.portfolio ? ` - ${alert.info.portfolio}` : ''}`}
                >
                  🚨 {alert.info.portfolio || alert.info.title}
                </button>
              ))}

              {/* Recent Charts */}
              {chartHistory.map((ticker) => (
                <button
                  key={ticker}
                  onClick={() => handleSelectTicker(ticker)}
                  className={`px-3 py-1 rounded text-sm font-medium whitespace-nowrap transition-colors flex-shrink-0 ${
                    selectedTableTicker === ticker
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                  title={`View ${ticker} chart`}
                >
                  📈 {ticker}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Portfolio Holdings Widget */}
        <div className="flex-1 overflow-auto p-4">
          {alertGridView?.portfolio && (
            <PortfolioHoldingsWidget
              portfolioName={alertGridView.portfolio}
              onClose={() => setRightPanelOpen(false)}
              filterTickers={alertGridView?.tickers}
            />
          )}
        </div>
      </div>
      )}

      {/* Old Alert Grid View - Hidden for now */}
      {false && (
      <div className="flex-1 flex flex-col bg-slate-900 rounded-lg border border-slate-800">
        {/* Mixed Recent Alerts & Charts Section - Top only */}
        {alertGridView && (alertHistory.length > 0 || chartHistory.length > 0) && (
          <div className="border-b border-slate-800 bg-slate-950 px-4 py-3">
            <div className="text-xs font-semibold text-slate-400 mb-2">Recent</div>
            <div className="flex gap-2 overflow-x-auto pb-2">
              {/* Recent Alerts */}
              {alertHistory.map((alert) => (
                <button
                  key={alert.id}
                  onClick={() => handleAlertGridClick(alert.info, alert.id)}
                  className={`px-3 py-1 rounded text-sm font-medium whitespace-nowrap transition-colors flex-shrink-0 ${
                    selectedAlertId === alert.id
                      ? 'bg-red-600 text-white'
                      : 'bg-red-900/30 text-red-300 hover:bg-red-900/50'
                  }`}
                  title={`${alert.info.title}${alert.info.portfolio ? ` - ${alert.info.portfolio}` : ''}`}
                >
                  🚨 {alert.info.portfolio || alert.info.title}
                </button>
              ))}

              {/* Recent Charts */}
              {chartHistory.map((ticker) => (
                <button
                  key={ticker}
                  onClick={() => handleSelectTicker(ticker)}
                  className={`px-3 py-1 rounded text-sm font-medium whitespace-nowrap transition-colors flex-shrink-0 ${
                    selectedTableTicker === ticker
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                  title={`View ${ticker} chart`}
                >
                  📈 {ticker}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Tabs and Controls - Always visible */}
        {alertGridView && (
          <>
            <div className="border-b border-slate-800 bg-slate-900">
              <div className="flex items-center justify-between px-4 py-3 gap-4">
                {/* Tab Navigation */}
                <div className="flex gap-8">
                  {(['table', 'charts'] as const).map((mode) => (
                    <button
                      key={mode}
                      onClick={() => setViewMode(mode)}
                      className={`px-1 py-2 font-medium text-sm transition border-b-2 ${
                        viewMode === mode
                          ? 'border-purple-600 text-white'
                          : 'border-transparent text-slate-400 hover:text-slate-300'
                      }`}
                    >
                      {mode === 'table' ? 'Table' : 'Charts'}
                    </button>
                  ))}
                </div>

                {/* Timeframe Selector - Only show in charts view */}
                {viewMode === 'charts' && (
                  <div className="flex items-center gap-3 flex-shrink-0">
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
                )}
              </div>
            </div>

            {/* Search Bar - Only show in table view */}
            {viewMode === 'table' && (
              <div className="border-b border-slate-800 bg-slate-950 px-4 py-3">
                <div className="flex gap-3">
                  <input
                    type="text"
                    placeholder="Search by symbol or company..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 rounded text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-600"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-sm transition flex-shrink-0"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {/* Content */}
        <div className="flex-1 overflow-hidden p-4">
          {alertGridView ? (
            viewMode === 'table' ? (
              <div className="h-full overflow-auto">
                {alertGridView.portfolio && portfolioPositions.length > 0 ? (
                  <PortfolioHoldingsTable
                    positions={portfolioPositions}
                    totalValue={portfolioPositions.reduce((sum: number, p: any) => sum + (p.position_value || 0), 0)}
                    currency="EUR"
                    filterTickers={alertGridView.tickers}
                    selectedPosition={selectedTableTicker}
                    showSearch={false}
                    showActions={false}
                    externalSearchQuery={searchQuery}
                    onSelectPosition={(ticker) => handleSelectTicker(ticker)}
                  />
                ) : (
                  <PortfolioHoldingsTable
                    positions={alertGridView.tickers.map((ticker) => {
                      const tickerData = historicalData[ticker] || []
                      const fund = fundamentalData[ticker] || {}
                      const filteredData = filterDataByTimeframe(tickerData, timeframe)
                      const currentPrice = fund.current_price || (tickerData.length > 0 ? tickerData[tickerData.length - 1].close : 0)
                      const previousClose = fund.previous_close || (tickerData.length > 1 ? tickerData[tickerData.length - 2].close : currentPrice)
                      const gain = (currentPrice || 0) - (previousClose || 0)
                      const gainPct = previousClose ? (gain / previousClose) * 100 : 0
                      console.log(`[Dashboard] Position ${ticker}: current=${currentPrice}, prev=${previousClose}, gain=${gain}`)

                      return {
                        ticker,
                        company_name: fund.company_name || ticker,
                        quantity: null, // Hide shares for non-portfolio alerts
                        avg_entry_price: previousClose || 0,
                        current_price: currentPrice || 0,
                        position_value: currentPrice || 0,
                        position_gain: gain,
                        position_gain_pct: gainPct,
                      }
                    })}
                    totalValue={alertGridView.tickers.reduce((sum, ticker) => {
                      const fund = fundamentalData[ticker] || {}
                      return sum + (fund.current_price || 0)
                    }, 0)}
                    currency="EUR"
                    fundamentalData={fundamentalData}
                    selectedPosition={selectedTableTicker}
                    showSearch={false}
                    showActions={false}
                    externalSearchQuery={searchQuery}
                    onSelectPosition={(ticker) => handleSelectTicker(ticker)}
                  />
                )}
              </div>
            ) : (
              <div className="h-full overflow-y-auto">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {alertGridView.tickers.map((ticker) => {
                    const tickerData = historicalData[ticker] || []
                    const fund = fundamentalData[ticker] || {}
                    const filteredData = filterDataByTimeframe(tickerData, timeframe)
                    const currentPrice = fund.current_price || (tickerData.length > 0 ? tickerData[tickerData.length - 1].close : 0)
                    const previousClose = fund.previous_close || (tickerData.length > 1 ? tickerData[tickerData.length - 2].close : currentPrice)

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
                        <div className="bg-slate-800/50 border-b border-slate-800 p-4">
                          <div className="flex items-start justify-between mb-3">
                            <div>
                              <p className="text-white font-bold text-lg">{ticker}</p>
                              <p className="text-slate-400 text-xs">{fund.company_name || ticker}</p>
                            </div>
                            <div className="text-right">
                              <p className={`text-2xl font-bold ${change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {change.toFixed(1)}%
                              </p>
                              <p className="text-slate-400 text-xs">Change</p>
                            </div>
                          </div>
                        </div>

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

                        <div className="border-t border-slate-800 p-4 text-center">
                          <p className="text-xs text-slate-400">Click to view chart</p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-slate-500">
                <div className="text-4xl mb-2">📢</div>
                <div className="text-sm">Click on an alert to view tickers</div>
              </div>
            </div>
          )}
        </div>
      </div>
      )}

      {/* Chart Modal */}
      {chartModalTicker && (
        <ChartModal
          ticker={chartModalTicker}
          onClose={() => setChartModalTicker(null)}
          timeframe={timeframe}
        />
      )}
    </div>
  )
}

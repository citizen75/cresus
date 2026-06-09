import { useState, useCallback, useEffect } from 'react'
import GlobalConversationPanel from '@/components/portfolio/GlobalConversationPanel'
import TradingChart from '@/components/TradingChart'
import CardChart from '@/components/CardChart'
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
            // Grid View - All Tickers
            <div className="h-full overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {alertGridView.tickers.map((ticker) => (
                  <div
                    key={ticker}
                    className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden hover:border-purple-600/50 transition cursor-pointer"
                    onClick={() => handleSelectTicker(ticker)}
                  >
                    {/* Card Header */}
                    <div className="bg-slate-800/50 border-b border-slate-800 p-3">
                      <div className="flex items-center justify-between">
                        <p className="text-white font-bold">{ticker}</p>
                        <span className="text-xl">📈</span>
                      </div>
                    </div>

                    {/* Chart */}
                    {historicalData[ticker] && historicalData[ticker].length > 0 ? (
                      <CardChart
                        data={historicalData[ticker].slice(-30)}
                        ticker={ticker}
                        showVariation={false}
                      />
                    ) : (
                      <div className="p-4 h-48 bg-slate-800/20 flex items-center justify-center">
                        <p className="text-slate-500 text-xs">Loading chart...</p>
                      </div>
                    )}

                    {/* Footer */}
                    <div className="border-t border-slate-800 px-3 py-2 bg-slate-800/30 text-center">
                      <p className="text-xs text-slate-400">Click to expand</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : selectedTicker ? (
            // Single Chart View
            <TradingChart ticker={selectedTicker} />
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

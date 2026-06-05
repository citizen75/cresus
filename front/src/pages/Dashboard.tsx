import { useState, useCallback } from 'react'
import GlobalConversationPanel from '@/components/portfolio/GlobalConversationPanel'
import TradingChart from '@/components/TradingChart'

export default function Dashboard() {
  const [conversationOpen, setConversationOpen] = useState(true)
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
  const [chartHistory, setChartHistory] = useState<string[]>([])

  const handleSelectTicker = useCallback((ticker: string) => {
    setSelectedTicker(ticker)
    // Add to history if not already there, keep last 10
    setChartHistory((prev) => {
      const filtered = prev.filter((t) => t !== ticker)
      return [ticker, ...filtered].slice(0, 10)
    })
  }, [])

  return (
    <div className="flex gap-6 h-[calc(100vh-120px)]">
      {/* Center Column - Conversations */}
      {conversationOpen && (
        <div className="w-[500px] flex-shrink-0">
          <GlobalConversationPanel
            onClose={() => setConversationOpen(false)}
            onAlertClick={handleSelectTicker}
          />
        </div>
      )}

      {/* Right Column - Chart */}
      <div className="flex-1 flex flex-col bg-slate-900 rounded-lg border border-slate-800">
        {/* Header */}
        <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">📈</span>
            <h3 className="text-sm font-semibold text-white">
              {selectedTicker ? selectedTicker : 'Chart'}
            </h3>
          </div>
          {selectedTicker && (
            <button
              onClick={() => setSelectedTicker(null)}
              className="text-slate-500 hover:text-slate-400"
            >
              ✕
            </button>
          )}
        </div>

        {/* Chart History */}
        {chartHistory.length > 0 && (
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
          {selectedTicker ? (
            <TradingChart ticker={selectedTicker} />
          ) : (
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

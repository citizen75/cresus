import { useEffect } from 'react'
import TradingChart from './TradingChart'

interface ChartModalProps {
  ticker: string
  onClose: () => void
  timeframe?: string
}

export function ChartModal({ ticker, onClose, timeframe = '1M' }: ChartModalProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 rounded-lg border border-slate-800 w-full max-w-5xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div>
            <h2 className="text-lg font-bold text-white">{ticker}</h2>
            <p className="text-sm text-slate-400">Chart View</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 text-2xl transition"
            title="Close (Esc)"
          >
            ✕
          </button>
        </div>

        {/* Chart */}
        <div className="flex-1 overflow-auto p-4">
          <TradingChart ticker={ticker} timeframe={timeframe} />
        </div>
      </div>
    </div>
  )
}

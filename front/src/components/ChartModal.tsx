import { useEffect } from 'react'
import TradingChartWidget from './TradingChartWidget'

interface ChartModalProps {
  ticker: string
  onClose: () => void
}

export function ChartModal({ ticker, onClose }: ChartModalProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 rounded-lg border border-slate-800 w-full max-w-6xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 flex-shrink-0">
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

        {/* Chart Widget */}
        <div className="flex-1 overflow-hidden px-4 py-4">
          <TradingChartWidget ticker={ticker} showControls={true} />
        </div>
      </div>
    </div>
  )
}

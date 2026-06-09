import React from 'react'

interface TradingChartControlsWidgetProps {
  timeframe: string
  onTimeframeChange: (tf: string) => void
  visibleWindow: '1M' | '3M' | '6M' | 'YTD' | '1Y' | '2Y'
  onVisibleWindowChange: (window: '1M' | '3M' | '6M' | 'YTD' | '1Y' | '2Y') => void
  selectedIndicators: Set<string>
  onToggleIndicator: (indicator: string) => void
  chartType?: string
  onChartTypeChange?: (type: string) => void
  hoverData?: Record<string, any>
}

export default function TradingChartControlsWidget({
  timeframe,
  onTimeframeChange,
  visibleWindow,
  onVisibleWindowChange,
  selectedIndicators,
  onToggleIndicator,
  chartType = 'Candlestick',
  onChartTypeChange,
  hoverData,
}: TradingChartControlsWidgetProps) {
  return (
    <div className="w-48 bg-slate-900 border-l border-slate-800 p-4 overflow-y-auto space-y-4">
      {/* Timeframe selector */}
      <div>
        <div className="text-xs font-bold text-slate-400 uppercase mb-2">Timeframe</div>
        <div className="grid grid-cols-3 gap-1">
          {['1D', '1W', '1M', '3M', '6M', '1Y'].map((tf) => (
            <button
              key={tf}
              onClick={() => onTimeframeChange(tf)}
              className={`py-1 px-2 text-xs rounded transition ${
                timeframe === tf
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Visible Window selector */}
      <div>
        <div className="text-xs font-bold text-slate-400 uppercase mb-2">Window</div>
        <div className="grid grid-cols-3 gap-1">
          {(['1M', '3M', '6M', 'YTD', '1Y', '2Y'] as const).map((window) => (
            <button
              key={window}
              onClick={() => onVisibleWindowChange(window)}
              className={`py-1 px-2 text-xs rounded transition ${
                visibleWindow === window
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              {window}
            </button>
          ))}
        </div>
      </div>

      {/* Indicators */}
      <div>
        <div className="text-xs font-bold text-slate-400 uppercase mb-2">Indicators</div>
        <div className="space-y-2">
          {['MA 20', 'MA 50', 'MA 200', 'RSI 14', 'MACD'].map((indicator) => (
            <label key={indicator} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="rounded border-slate-600"
                checked={selectedIndicators.has(indicator)}
                onChange={() => onToggleIndicator(indicator)}
              />
              <span className="text-sm text-slate-300">{indicator}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Chart Type */}
      {onChartTypeChange && (
        <div>
          <div className="text-xs font-bold text-slate-400 uppercase mb-2">Chart Type</div>
          <div className="space-y-1">
            {['Candlestick', 'Line', 'Bars'].map((type) => (
              <button
                key={type}
                onClick={() => onChartTypeChange(type)}
                className={`w-full text-left px-3 py-2 text-sm rounded transition ${
                  type === chartType
                    ? 'bg-purple-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* All Indicators Cached */}
      <div>
        <div className="text-xs font-bold text-slate-400 uppercase mb-2">All Indicators</div>
        <div className="space-y-1 max-h-80 overflow-y-auto text-xs">
          {hoverData &&
            Object.keys(hoverData)
              .filter(
                (key) =>
                  !['open', 'high', 'low', 'close', 'volume'].includes(key.toLowerCase())
              )
              .sort()
              .map((key) => {
                const value = hoverData[key]
                const displayValue =
                  value !== undefined && value !== null
                    ? typeof value === 'number'
                      ? value.toFixed(3)
                      : value
                    : '—'
                return (
                  <div
                    key={key}
                    className="flex justify-between items-center px-2 py-1 rounded bg-slate-800/50 hover:bg-slate-800 transition"
                  >
                    <span className="text-slate-300">{key}</span>
                    <span className="text-slate-400 font-mono">{displayValue}</span>
                  </div>
                )
              })}
          {(!hoverData ||
            Object.keys(hoverData)
              .filter(
                (key) =>
                  !['open', 'high', 'low', 'close', 'volume'].includes(key.toLowerCase())
              ).length === 0) && (
            <div className="text-xs text-slate-500 px-2 py-4 text-center">
              No indicators available
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

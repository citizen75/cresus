import { useState } from 'react'
import TradingChart from './TradingChart'
import TradingChartControlsWidget from './TradingChartControlsWidget'

interface TradingChartWidgetProps {
  ticker: string
  title?: string
  showControls?: boolean
}

export default function TradingChartWidget({
  ticker,
  title,
  showControls = true,
}: TradingChartWidgetProps) {
  const [timeframe, setTimeframe] = useState('1D')
  const [visibleWindow, setVisibleWindow] = useState<'1M' | '3M' | '6M' | 'YTD' | '1Y' | '2Y'>('1Y')
  const [selectedIndicators, setSelectedIndicators] = useState<Set<string>>(new Set(['RSI 14', 'MACD']))
  const [chartType, setChartType] = useState('Candlestick')
  const [hoverData, setHoverData] = useState<any>(null)

  const handleToggleIndicator = (indicator: string) => {
    const newIndicators = new Set(selectedIndicators)
    if (newIndicators.has(indicator)) {
      newIndicators.delete(indicator)
    } else {
      newIndicators.add(indicator)
    }
    setSelectedIndicators(newIndicators)
  }

  return (
    <div className="flex h-full gap-4 bg-slate-950">
      {/* Left - Chart */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {title && (
          <div className="px-4 py-3 border-b border-slate-800 flex-shrink-0">
            <h2 className="text-lg font-bold text-white">{title || ticker}</h2>
          </div>
        )}
        <div className="flex-1 overflow-hidden">
          <TradingChart
            timeframe={timeframe}
            ticker={ticker}
            selectedIndicators={selectedIndicators}
            visibleWindow={visibleWindow}
            onCursorMove={setHoverData}
          />
        </div>
      </div>

      {/* Right - Controls */}
      {showControls && (
        <TradingChartControlsWidget
          timeframe={timeframe}
          onTimeframeChange={setTimeframe}
          visibleWindow={visibleWindow}
          onVisibleWindowChange={setVisibleWindow}
          selectedIndicators={selectedIndicators}
          onToggleIndicator={handleToggleIndicator}
          chartType={chartType}
          onChartTypeChange={setChartType}
          hoverData={hoverData}
        />
      )}
    </div>
  )
}

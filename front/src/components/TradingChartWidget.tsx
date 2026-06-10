import { useState, useEffect } from 'react'
import TradingChart from './TradingChart'
import TradingChartControlsWidget from './TradingChartControlsWidget'
import { useHistoricalDataLoader } from '@/hooks/useHistoricalDataLoader'
import { api } from '@/services/api'

interface TradingChartWidgetProps {
  ticker: string
  title?: string
  showControls?: boolean
  onGetHistoricalData?: (ticker: string, days: number) => Promise<any>
}

export default function TradingChartWidget({
  ticker,
  title,
  showControls = true,
  onGetHistoricalData,
}: TradingChartWidgetProps) {
  const [timeframe, setTimeframe] = useState('1D')
  const [visibleWindow, setVisibleWindow] = useState<'1M' | '3M' | '6M' | 'YTD' | '1Y' | '2Y'>('1Y')
  const [selectedIndicators, setSelectedIndicators] = useState<Set<string>>(new Set(['RSI 14', 'MACD']))
  const [chartType, setChartType] = useState('Candlestick')
  const [hoverData, setHoverData] = useState<any>(null)

  // Use centralized data loader
  const { loadData } = useHistoricalDataLoader()
  const [chartData, setChartData] = useState<any[] | undefined>(undefined)

  // Load chart data on mount or when ticker changes
  useEffect(() => {
    const fetchData = async () => {
      const fetchFn = onGetHistoricalData || api.getHistoricalData.bind(api)
      const data = await loadData([ticker], fetchFn)
      if (data && data[ticker]) {
        setChartData(data[ticker])
      }
    }
    fetchData()
  }, [ticker, loadData, onGetHistoricalData])

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
            chartData={chartData}
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

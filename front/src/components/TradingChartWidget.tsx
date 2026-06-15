import { useState, useEffect, useRef } from 'react'
import TradingChart from './TradingChart'
import TradingChartControlsWidget from './TradingChartControlsWidget'
import { useHistoricalDataLoader } from '@/hooks/useHistoricalDataLoader'
import { api } from '@/services/api'

import { logger } from '@/services/logger'
interface TradingChartWidgetProps {
  ticker: string
  title?: string
  showControls?: boolean
  onGetHistoricalData?: (ticker: string, days: number) => Promise<any>
  dataCache?: Map<string, any[]>
}

export default function TradingChartWidget({
  ticker,
  title,
  showControls = true,
  onGetHistoricalData,
  dataCache,
}: TradingChartWidgetProps) {
  const [timeframe, setTimeframe] = useState('1D')
  const [visibleWindow, setVisibleWindow] = useState<'1M' | '3M' | '6M' | 'YTD' | '1Y' | '2Y'>('1Y')
  const [selectedIndicators, setSelectedIndicators] = useState<Set<string>>(new Set(['RSI 14', 'MACD']))
  const [chartType, setChartType] = useState('Candlestick')
  const [hoverData, setHoverData] = useState<any>(null)

  // Use centralized data loader
  const { loadData } = useHistoricalDataLoader()
  const [chartData, setChartData] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(false)

  // Track which ticker we're currently fetching to prevent duplicate requests
  const fetchingTickerRef = useRef<string | null>(null)

  // Use provided cache or create a local one
  const cache = dataCache || useRef<Record<string, any[]>>({})

  // Load chart data on mount or when ticker changes
  useEffect(() => {
    // Skip if we're already fetching this ticker
    if (fetchingTickerRef.current === ticker) return

    // Clear old data immediately when ticker changes
    setChartData(undefined)

    const fetchData = async () => {
      fetchingTickerRef.current = ticker

      // Check cache first (handle both Map and object formats)
      let cachedData
      if (dataCache instanceof Map) {
        cachedData = dataCache.get(ticker)
      } else if (cache && typeof cache === 'object' && 'current' in cache) {
        cachedData = (cache as any).current[ticker]
      }

      if (cachedData) {
        logger.debug(`⚡ Using cached data for ${ticker}`)
        setChartData(cachedData)
        setIsLoading(false)
        fetchingTickerRef.current = null
        return
      }

      try {
        setIsLoading(true)
        console.log(`[TradingChartWidget] Fetching data for ${ticker}...`)
        logger.debug(`📡 Fetching data for ${ticker}...`)
        let response
        if (onGetHistoricalData) {
          // Custom fetch function - call with just ticker and days
          console.log(`[TradingChartWidget] Using custom onGetHistoricalData`)
          response = await onGetHistoricalData(ticker, 730)
        } else {
          // Use default API with sha_10 indicator
          console.log(`[TradingChartWidget] Using default API getHistoricalData`)
          response = await api.getHistoricalData(ticker, 730, { indicator: 'sha_10' })
        }
        console.log(`[TradingChartWidget] Response:`, response)
        if (response && response.data) {
          // Cache the data in the appropriate format
          if (dataCache instanceof Map) {
            dataCache.set(ticker, response.data)
          } else if (cache && typeof cache === 'object' && 'current' in cache) {
            (cache as any).current[ticker] = response.data
          }
          logger.debug(`✅ Setting chart data: ${response.data.length} rows for ${ticker}`)
          console.log(`[TradingChartWidget] Setting chartData for ${ticker}:`, response.data)
          setChartData(response.data)
        } else {
          logger.warning(`No data in response for ${ticker}`)
          console.log(`[TradingChartWidget] No data in response:`, response)
          setChartData([])
        }
      } finally {
        setIsLoading(false)
        fetchingTickerRef.current = null
      }
    }
    fetchData()
  }, [ticker, dataCache, cache])  // Depend on cache reference too

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
        <div className="flex-1 overflow-hidden">
          <TradingChart
            timeframe={timeframe}
            ticker={ticker}
            selectedIndicators={selectedIndicators}
            visibleWindow={visibleWindow}
            onCursorMove={setHoverData}
            chartData={chartData}
            isLoading={isLoading}
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

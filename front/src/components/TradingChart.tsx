import { useEffect, useRef, useState } from 'react'
import { api } from '@/services/api'
import IndicatorsPanel from './IndicatorsPanel'

interface TradingChartProps {
  timeframe: string
  title?: string
  ticker?: string
  entryDate?: string
  exitDate?: string
  selectedIndicators?: Set<string>
  chartData?: any[]
  visibleWindow?: '1M' | '3M' | '6M' | 'YTD' | '1Y' | '2Y'
}

export default function TradingChart({ timeframe, title = 'Price Chart', ticker, entryDate, exitDate, selectedIndicators = new Set(), chartData: externalChartData, visibleWindow = '1Y' }: TradingChartProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [companyName, setCompanyName] = useState<string>('')
  const [chartData, setChartData] = useState<any[]>([])
  const [shaCandles, setShaCandles] = useState<any[]>([])
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const indicatorChartsRef = useRef<{ rsi?: any; macd?: any; mainChart?: any }>({})
  const lastCursorPosRef = useRef<any>(null)

  const randomNumber = (min: number, max: number) => Math.random() * (max - min) + min

  const calculateMACD = (data: any[]): { line: (number | null)[]; signal: (number | null)[]; histogram: (number | null)[] } => {
    const ema12 = calculateEMA(data, 12)
    const ema26 = calculateEMA(data, 26)
    const line = ema12.map((v, i) => (v && ema26[i] ? v - ema26[i] : null))
    const signal = calculateEMA(line.map(v => ({ close: v || 0 })), 9)
    const histogram = line.map((v, i) => (v && signal[i] ? v - signal[i] : null))
    return { line, signal, histogram }
  }

  const calculateRSI = (data: any[], period: number = 14): (number | null)[] => {
    const rsi: (number | null)[] = new Array(data.length).fill(null)
    if (data.length < period) return rsi

    let gainSum = 0,
      lossSum = 0
    for (let i = 1; i <= period; i++) {
      const change = data[i].close - data[i - 1].close
      if (change > 0) gainSum += change
      else lossSum -= change
    }

    for (let i = period; i < data.length; i++) {
      const avgGain = gainSum / period
      const avgLoss = lossSum / period
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss
      rsi[i] = 100 - 100 / (1 + rs)

      const change = data[i].close - data[i - 1].close
      gainSum -= gainSum / period
      lossSum -= lossSum / period
      if (change > 0) gainSum += change
      else lossSum -= change
    }
    return rsi
  }

  const calculateEMA = (data: any[], period: number): (number | null)[] => {
    const ema: (number | null)[] = new Array(data.length).fill(null)
    if (data.length < period) return ema

    let sum = 0
    for (let i = 0; i < period; i++) {
      sum += data[i].close
    }
    const k = 2 / (period + 1)
    ema[period - 1] = sum / period

    for (let i = period; i < data.length; i++) {
      ema[i] = data[i].close * k + (ema[i - 1] || 0) * (1 - k)
    }
    return ema
  }

  const randomBar = (lastClose: number) => {
    const open = +randomNumber(lastClose * 0.95, lastClose * 1.05).toFixed(2)
    const close = +randomNumber(open * 0.95, open * 1.05).toFixed(2)
    const high = +randomNumber(Math.max(open, close), Math.max(open, close) * 1.1).toFixed(2)
    const low = +randomNumber(Math.min(open, close) * 0.9, Math.min(open, close)).toFixed(2)
    const volume = Math.floor(randomNumber(1000000, 6000000))
    return { open: +open, high: +high, low: +low, close: +close, volume }
  }

  const generateCandleData = (numberOfPoints = 500) => {
    const data = []
    const date = new Date()
    date.setUTCDate(date.getUTCDate() - numberOfPoints)

    let lastClose = 75
    for (let i = 0; i < numberOfPoints; i++) {
      const candle = randomBar(lastClose)
      lastClose = candle.close
      const dateStr = date.toISOString().split('T')[0]

      data.push({
        time: dateStr,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      })

      date.setUTCDate(date.getUTCDate() + 1)
    }
    return data
  }

  const generateVolumeData = (candleData: any[]) => {
    let lastClose = 75
    return candleData.map(candle => {
      const randomCandle = randomBar(lastClose)
      lastClose = randomCandle.close
      const color = candle.close >= candle.open ? '#26a69a' : '#ef5350'
      return {
        time: candle.time,
        value: randomCandle.volume,
        color,
      }
    })
  }

  const generateDatasets = (timeframe: string) => {
    // Always load 2 years of data for consistent view
    const candles = generateCandleData(730)
    const volume = generateVolumeData(candles)
    return { candles, volume }
  }

  // Fetch fundamental data (company name) when ticker changes
  useEffect(() => {
    if (!ticker) {
      setCompanyName('')
      return
    }

    const fetchFundamental = async () => {
      try {
        const data = await api.getFundamental(ticker)
        setCompanyName(data.data?.company?.name || '')
      } catch (err) {
        console.error('Failed to fetch fundamental data:', err)
        setCompanyName('')
      }
    }

    fetchFundamental()
  }, [ticker])

  useEffect(() => {
    if (!containerRef.current) return

    let resizeHandler: (() => void) | null = null
    let isMounted = true

    const setupChart = async () => {
      try {
        setIsLoading(true)

        // Forcefully clear and remove any existing chart
        if (chartRef.current) {
          try {
            chartRef.current.remove()
          } catch (e) {
            // Ignore
          }
        }

        if (containerRef.current) {
          containerRef.current.innerHTML = ''
        }

        if (!isMounted) return

        const lwc = await import('lightweight-charts')
        const { createChart, CandlestickSeries, HistogramSeries, LineSeries, createSeriesMarkers } = lwc

        // Fetch real data if ticker provided, otherwise generate sample data
        let candles: any[] = []
        let volume: any[] = []

        if (ticker) {
          try {
            // Fetch historical data with SHA_10 indicator
            const response = await api.getHistoricalData(ticker, 730, { indicator: 'sha_10' } as any)
            // Response has structure: { ticker, count, days, indicator, data: [...records] }
            const data = (response as any).data || []

            if (data.length === 0) {
              throw new Error(`No data available for ${ticker}`)
            }

            candles = data.map((d: any) => ({
              time: d.timestamp.substring(0, 10),
              open: parseFloat(d.open),
              high: parseFloat(d.high),
              low: parseFloat(d.low),
              close: parseFloat(d.close),
            }))

            // Extract SHA candlestick data if available
            const shaData = data
              .filter((d: any) => d.sha_10_open && d.sha_10_high && d.sha_10_low && d.sha_10_close)
              .map((d: any) => ({
                time: d.timestamp.substring(0, 10),
                open: parseFloat(d.sha_10_open),
                high: parseFloat(d.sha_10_high),
                low: parseFloat(d.sha_10_low),
                close: parseFloat(d.sha_10_close),
              }))

            volume = data.map((d: any) => {
              const color = parseFloat(d.close) >= parseFloat(d.open) ? '#26a69a' : '#ef5350'
              return {
                time: d.timestamp.substring(0, 10),
                value: parseInt(d.volume),
                color,
              }
            })

            console.log(`Loaded ${candles.length} candles for ${ticker} (SHA_10: ${shaData.length})`)
            setChartData(candles)
            setShaCandles(shaData)
          } catch (err) {
            console.error('Failed to fetch historical data:', err)
            const { candles: genCandles, volume: genVolume } = generateDatasets(timeframe)
            candles = genCandles
            volume = genVolume
            setChartData(candles)
          }
        } else {
          const { candles: genCandles, volume: genVolume } = generateDatasets(timeframe)
          candles = genCandles
          volume = genVolume
          setChartData(candles)
        }

        if (!containerRef.current) return

        const chart = createChart(containerRef.current, {
          layout: {
            background: { color: '#0f172a' },
            textColor: '#94a3b8',
          },
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
          rightPriceScale: {
            borderVisible: false,
          },
          grid: {
            vertLines: { visible: false },
            horzLines: { visible: false },
          },
        })

        if (!isMounted) {
          chart.remove()
          return
        }

        chartRef.current = chart

        // Store main chart reference for indicator charts to sync back
        indicatorChartsRef.current.mainChart = chart

        // Store series constructor for later use (e.g., adding SHA candlesticks)
        ;(chartRef.current as any).CandlestickSeries = CandlestickSeries

        // Pane 0: Candlesticks + Volume + EMAs
        const candlestickSeries = chart.addSeries(CandlestickSeries, {
          upColor: '#10b981',
          downColor: '#ef4444',
          borderVisible: false,
          wickUpColor: '#10b981',
          wickDownColor: '#ef4444',
        }, 0)

        candlestickSeries.setData(candles)
        candlestickSeries.priceScale().applyOptions({
          scaleMargins: {
            top: 0.05,
            bottom: 0.15,
          },
        })

        // Store candlestick series on chart for crosshair syncing
        ;(chart as any).candlestickSeries = candlestickSeries

        // Add EMA series - calculated on full dataset before visible window is applied
        const emaColors: { [key: number]: string } = {
          10: '#ff6b6b',
          20: '#4ecdc4',
          50: '#ffe66d',
          100: '#a29bfe',
          200: '#74b9ff',
        }

        const emaPeriods = [10, 20, 50, 100, 200]
        for (const period of emaPeriods) {
          const emaValues = calculateEMA(candles, period)
          const emaData = candles
            .map((candle, i) => ({
              time: candle.time,
              value: emaValues[i],
            }))
            .filter(d => d.value !== null)

          const emaSeries = chart.addSeries(LineSeries, {
            color: emaColors[period],
            lineWidth: 1,
          })
          emaSeries.setData(emaData)
        }

        const markers: any[] = []

        if (entryDate) {
          const entryDateObj = new Date(entryDate)
          markers.push({
            time: {
              year: entryDateObj.getFullYear(),
              month: entryDateObj.getMonth() + 1,
              day: entryDateObj.getDate()
            },
            position: 'belowBar',
            color: '#FFEB3B',
            shape: 'arrowUp',
            text: 'ENTRY',
          })
        }

        if (exitDate) {
          const exitDateObj = new Date(exitDate)
          markers.push({
            time: {
              year: exitDateObj.getFullYear(),
              month: exitDateObj.getMonth() + 1,
              day: exitDateObj.getDate()
            },
            position: 'aboveBar',
            color: '#FFEB3B',
            shape: 'arrowDown',
            text: 'EXIT',
          })
        }

        if (markers.length > 0) {
          createSeriesMarkers(candlestickSeries, markers)
        }

        const volumeSeries = chart.addSeries(HistogramSeries, {
          priceFormat: { type: 'volume' },
          priceScaleId: '',
        }, 0)

        volumeSeries.setData(volume)
        volumeSeries.priceScale().applyOptions({
          scaleMargins: {
            top: 0.85,
            bottom: 0,
          },
        })

        chart.timeScale().fitContent()

        // Sync crosshair across all charts
        const unsubscribeCrosshair = chart.subscribeCrosshairMove((param) => {
          lastCursorPosRef.current = param

          if (!param.time) {
            if (indicatorChartsRef.current.rsi) {
              indicatorChartsRef.current.rsi.clearCrosshairPosition()
            }
            if (indicatorChartsRef.current.macd) {
              indicatorChartsRef.current.macd.clearCrosshairPosition()
            }
            return
          }

          // Sync to RSI chart - just sync the time position
          if (indicatorChartsRef.current.rsi) {
            const rsiChart = indicatorChartsRef.current.rsi as any
            if (rsiChart.rsiSeries) {
              rsiChart.setCrosshairPosition(0, param.time, rsiChart.rsiSeries)
            }
          }

          // Sync to MACD chart - just sync the time position
          if (indicatorChartsRef.current.macd) {
            const macdChart = indicatorChartsRef.current.macd as any
            if (macdChart.macdSeries) {
              macdChart.setCrosshairPosition(0, param.time, macdChart.macdSeries)
            }
          }
        })

        resizeHandler = () => {
          if (containerRef.current && chartRef.current) {
            chartRef.current.applyOptions({
              width: containerRef.current.clientWidth,
              height: containerRef.current.clientHeight,
            })
          }
        }

        window.addEventListener('resize', resizeHandler)
        setIsLoading(false)

        // Store unsubscribe function for cleanup
        if (!chartRef.current) chartRef.current = {}
        chartRef.current.unsubscribeCrosshair = unsubscribeCrosshair
      } catch (error) {
        console.error('Chart error:', error)
        setIsLoading(false)
      }
    }

    setupChart()

    return () => {
      isMounted = false
      if (resizeHandler) {
        window.removeEventListener('resize', resizeHandler)
      }
      if (chartRef.current) {
        try {
          if (chartRef.current.unsubscribeCrosshair) {
            chartRef.current.unsubscribeCrosshair()
          }
          chartRef.current.remove()
        } catch (e) {
          // Ignore
        }
        chartRef.current = null
      }
    }
  }, [timeframe, ticker, entryDate, exitDate])

  // Add SHA candlesticks series when data becomes available
  useEffect(() => {
    if (!chartRef.current || !shaCandles || shaCandles.length === 0) return

    try {
      const CandlestickSeries = (chartRef.current as any).CandlestickSeries

      if (!CandlestickSeries) {
        console.warn('CandlestickSeries not available')
        return
      }

      const shaSeries = chartRef.current.addSeries(CandlestickSeries, {
        upColor: 'rgba(147, 112, 219, 0.6)',  // Purple
        downColor: 'rgba(220, 20, 60, 0.6)',  // Crimson
        borderVisible: false,
        wickUpColor: 'rgba(147, 112, 219, 0.6)',
        wickDownColor: 'rgba(220, 20, 60, 0.6)',
      }, 0)

      shaSeries.setData(shaCandles)
      shaSeries.priceScale().applyOptions({
        scaleMargins: {
          top: 0.05,
          bottom: 0.15,
        },
      })
    } catch (err) {
      console.error('Error adding SHA candlesticks:', err)
    }
  }, [shaCandles])

  // Set visible range based on visibleWindow
  useEffect(() => {
    if (!chartRef.current || !chartData.length) return

    const now = new Date()
    const getWindowStart = () => {
      const start = new Date(now)
      switch (visibleWindow) {
        case '1M':
          start.setMonth(start.getMonth() - 1)
          break
        case '3M':
          start.setMonth(start.getMonth() - 3)
          break
        case '6M':
          start.setMonth(start.getMonth() - 6)
          break
        case 'YTD':
          start.setFullYear(start.getFullYear(), 0, 1)
          break
        case '1Y':
          start.setFullYear(start.getFullYear() - 1)
          break
        case '2Y':
          start.setFullYear(start.getFullYear() - 2)
          break
      }
      return start.getTime() / 1000
    }

    const startTime = getWindowStart()
    const filteredData = chartData.filter((d) => {
      const [year, month, day] = d.time.split('-').map(Number)
      const date = new Date(year, month - 1, day).getTime() / 1000
      return date >= startTime
    })

    if (filteredData.length > 0) {
      const firstCandle = filteredData[0]
      const lastCandle = filteredData[filteredData.length - 1]
      chartRef.current.timeScale().setVisibleRange({
        from: firstCandle.time,
        to: lastCandle.time,
      })
    }
  }, [visibleWindow, chartData])

  return (
    <div className="flex flex-col h-full">
      <div className="bg-slate-900 border-b border-slate-800 px-6 py-3 flex-shrink-0">
        <div className="text-white font-bold text-lg">{ticker}</div>
        {companyName && <div className="text-sm text-slate-400">{companyName}</div>}
      </div>
      <div className="flex-1 flex flex-col min-h-0">
        <div className="flex-grow" ref={containerRef} />
        {selectedIndicators.size > 0 && (
          <div className="flex-shrink-0 overflow-hidden">
            <IndicatorsPanel chartData={chartData} selectedIndicators={selectedIndicators} visibleWindow={visibleWindow} chartsRef={indicatorChartsRef} />
          </div>
        )}
      </div>
    </div>
  )
}

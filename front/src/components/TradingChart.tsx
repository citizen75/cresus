import { useEffect, useRef, useState } from 'react'
import { api } from '@/services/api'

interface TradingChartProps {
  timeframe: string
  title?: string
  ticker?: string
  entryDate?: string
  exitDate?: string
}

export default function TradingChart({ timeframe, title = 'Price Chart', ticker, entryDate, exitDate }: TradingChartProps) {
  const [isLoading, setIsLoading] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)

  const randomNumber = (min: number, max: number) => Math.random() * (max - min) + min

  const randomBar = (lastClose: number) => {
    const open = +randomNumber(lastClose * 0.95, lastClose * 1.05).toFixed(2)
    const close = +randomNumber(open * 0.95, open * 1.05).toFixed(2)
    const high = +randomNumber(Math.max(open, close), Math.max(open, close) * 1.1).toFixed(2)
    const low = +randomNumber(Math.min(open, close) * 0.9, Math.min(open, close)).toFixed(2)
    const volume = Math.floor(randomNumber(1000000, 6000000))
    return { open: +open, high: +high, low: +low, close: +close, volume }
  }

  const generateCandleData = (numberOfPoints = 500, referenceDate?: Date) => {
    const data = []
    const date = new Date(referenceDate || new Date())
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
    let points = 500
    if (timeframe === '1W') points = 250
    if (timeframe === '1M') points = 120
    if (timeframe === '3M') points = 90
    if (timeframe === '6M') points = 180
    if (timeframe === '1Y') points = 52

    // If markers provided, generate data around those dates
    let referenceDate: Date | undefined
    if (entryDate || exitDate) {
      const targetDate = new Date(exitDate || entryDate!)
      const futureBuffer = Math.ceil(points * 0.3)
      referenceDate = new Date(targetDate)
      referenceDate.setDate(referenceDate.getDate() + futureBuffer)
      console.log('Chart data range for marker:', {
        entryDate,
        exitDate,
        targetDate: targetDate.toISOString().split('T')[0],
        referenceDate: referenceDate.toISOString().split('T')[0],
        points,
      })
    }

    const candles = generateCandleData(points, referenceDate)
    const volume = generateVolumeData(candles)
    return { candles, volume }
  }

  useEffect(() => {
    if (!containerRef.current) return

    const setupChart = async () => {
      try {
        setIsLoading(true)
        const lwc = await import('lightweight-charts')
        const { createChart, CandlestickSeries, HistogramSeries } = lwc

        if (chartRef.current) {
          chartRef.current.remove()
        }

        // Fetch real data if ticker provided, otherwise generate sample data
        let candles: any[] = []
        let volume: any[] = []

        if (ticker) {
          try {
            const response = await api.getHistoricalData(ticker, 730)
            const data = response.data || []

            candles = data.map((d: any) => ({
              time: d.timestamp.substring(0, 10),
              open: d.open,
              high: d.high,
              low: d.low,
              close: d.close,
            }))

            volume = data.map((d: any) => {
              const prevOpen = d.open
              const color = d.close >= prevOpen ? '#26a69a' : '#ef5350'
              return {
                time: d.timestamp.substring(0, 10),
                value: d.volume,
                color,
              }
            })

            console.log(`Loaded ${candles.length} candles for ${ticker}`)
          } catch (err) {
            console.error('Failed to fetch historical data:', err)
            const { candles: genCandles, volume: genVolume } = generateDatasets(timeframe)
            candles = genCandles
            volume = genVolume
          }
        } else {
          const { candles: genCandles, volume: genVolume } = generateDatasets(timeframe)
          candles = genCandles
          volume = genVolume
        }

        const chart = createChart(containerRef.current!, {
          layout: {
            background: { color: '#0f172a' },
            textColor: '#94a3b8',
          },
          width: containerRef.current!.clientWidth,
          height: containerRef.current!.clientHeight,
          rightPriceScale: {
            borderVisible: false,
          },
          grid: {
            vertLines: { visible: false },
            horzLines: { visible: false },
          },
        })

        chartRef.current = chart

        const candlestickSeries = chart.addSeries(CandlestickSeries, {
          upColor: '#10b981',
          downColor: '#ef4444',
          borderVisible: false,
          wickUpColor: '#10b981',
          wickDownColor: '#ef4444',
        })

        candlestickSeries.setData(candles)
        candlestickSeries.priceScale().applyOptions({
          scaleMargins: {
            top: 0.05,
            bottom: 0.15,
          },
        })

        // Add entry/exit markers
        const markers: any[] = []
        if (entryDate) {
          const entryDateStr = new Date(entryDate).toISOString().substring(0, 10)
          markers.push({
            time: entryDateStr,
            position: 'belowBar',
            color: '#10b981',
            shape: 'arrowUp',
            text: 'Entry',
          })
          console.log('Entry marker:', entryDateStr)
        }
        if (exitDate) {
          const exitDateStr = new Date(exitDate).toISOString().substring(0, 10)
          markers.push({
            time: exitDateStr,
            position: 'aboveBar',
            color: '#ef4444',
            shape: 'arrowDown',
            text: 'Exit',
          })
          console.log('Exit marker:', exitDateStr)
        }
        if (markers.length > 0) {
          console.log('Chart data range:', candles[0]?.time, 'to', candles[candles.length - 1]?.time)
          console.log('Markers to set:', markers)
          console.log('Candle dates sample:', candles.slice(0, 5).map(c => c.time), '...', candles.slice(-5).map(c => c.time))
          candlestickSeries.setMarkers(markers)
          console.log('Markers set successfully')
        }

        const volumeSeries = chart.addSeries(HistogramSeries, {
          priceFormat: { type: 'volume' },
          priceScaleId: '',
        })

        volumeSeries.setData(volume)
        volumeSeries.priceScale().applyOptions({
          scaleMargins: {
            top: 0.85,
            bottom: 0,
          },
        })

        chart.timeScale().fitContent()

        const handleResize = () => {
          if (containerRef.current && chartRef.current) {
            chartRef.current.applyOptions({
              width: containerRef.current.clientWidth,
              height: containerRef.current.clientHeight,
            })
          }
        }

        window.addEventListener('resize', handleResize)
        setIsLoading(false)
        return () => window.removeEventListener('resize', handleResize)
      } catch (error) {
        console.error('Chart error:', error)
        setIsLoading(false)
      }
    }

    setupChart()
  }, [timeframe, ticker, entryDate, exitDate])

  return (
    <div className="flex flex-col h-full">
      <div className="text-xs text-slate-400 px-4 py-2">{title} ({timeframe})</div>
      <div className="flex-1" ref={containerRef} />
    </div>
  )
}

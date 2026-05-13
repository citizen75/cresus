import { useEffect, useRef } from 'react'

interface TradingChartProps {
  timeframe: string
  title?: string
  entryDate?: string
  exitDate?: string
}

export default function TradingChart({ timeframe, title = 'Price Chart', entryDate, exitDate }: TradingChartProps) {
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
    let points = 500
    if (timeframe === '1W') points = 250
    if (timeframe === '1M') points = 120
    if (timeframe === '3M') points = 90
    if (timeframe === '6M') points = 180
    if (timeframe === '1Y') points = 52

    const candles = generateCandleData(points)
    const volume = generateVolumeData(candles)
    return { candles, volume }
  }

  useEffect(() => {
    if (!containerRef.current) return

    const setupChart = async () => {
      try {
        const lwc = await import('lightweight-charts')
        const { createChart, CandlestickSeries, HistogramSeries } = lwc

        if (chartRef.current) {
          chartRef.current.remove()
        }

        const { candles, volume } = generateDatasets(timeframe)

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
          const entryDateStr = new Date(entryDate).toISOString().split('T')[0]
          markers.push({
            time: entryDateStr,
            position: 'belowBar',
            color: '#10b981',
            shape: 'arrowUp',
            text: 'Entry',
          })
        }
        if (exitDate) {
          const exitDateStr = new Date(exitDate).toISOString().split('T')[0]
          markers.push({
            time: exitDateStr,
            position: 'aboveBar',
            color: '#ef4444',
            shape: 'arrowDown',
            text: 'Exit',
          })
        }
        if (markers.length > 0) {
          candlestickSeries.setMarkers(markers)
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
        return () => window.removeEventListener('resize', handleResize)
      } catch (error) {
        console.error('Chart error:', error)
      }
    }

    setupChart()
  }, [timeframe, entryDate, exitDate])

  return (
    <div className="flex flex-col h-full">
      <div className="text-xs text-slate-400 px-4 py-2">{title} ({timeframe})</div>
      <div className="flex-1" ref={containerRef} />
    </div>
  )
}

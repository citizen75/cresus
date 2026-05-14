import { useEffect, useRef, useState } from 'react'

interface IndicatorsPanelProps {
  chartData: any[]
  selectedIndicators: Set<string>
  visibleWindow?: '1M' | '3M' | '6M' | 'YTD' | '1Y' | '2Y'
  chartsRef?: React.MutableRefObject<{ rsi?: any; macd?: any; mainChart?: any }>
}

export default function IndicatorsPanel({ chartData, selectedIndicators, visibleWindow = '1Y', chartsRef }: IndicatorsPanelProps) {
  const rsiContainerRef = useRef<HTMLDivElement>(null)
  const macdContainerRef = useRef<HTMLDivElement>(null)
  const rsiChartRef = useRef<any>(null)
  const macdChartRef = useRef<any>(null)

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

  const calculateMACD = (data: any[]): { line: (number | null)[]; signal: (number | null)[]; histogram: (number | null)[] } => {
    const ema12 = calculateEMA(data, 12)
    const ema26 = calculateEMA(data, 26)
    const line = ema12.map((v, i) => (v && ema26[i] ? v - ema26[i] : null))
    const signal = calculateEMA(line.map(v => ({ close: v || 0 })), 9)
    const histogram = line.map((v, i) => (v && signal[i] ? v - signal[i] : null))
    return { line, signal, histogram }
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

  const getVisibleRange = () => {
    if (!chartData.length) return null

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
      return {
        from: filteredData[0].time,
        to: filteredData[filteredData.length - 1].time,
      }
    }
    return null
  }

  useEffect(() => {
    if (!chartData.length) return

    const setupRSI = async () => {
      if (!selectedIndicators.has('RSI 14') || !rsiContainerRef.current) return

      try {
        const lwc = await import('lightweight-charts')
        const { createChart, LineSeries } = lwc

        if (rsiChartRef.current) {
          rsiChartRef.current.remove()
        }

        const rsi = calculateRSI(chartData, 14)
        const rsiData = chartData
          .map((candle, i) => ({
            time: candle.time,
            value: rsi[i],
          }))
          .filter(d => d.value !== null)

        const chart = createChart(rsiContainerRef.current, {
          layout: { background: { color: '#0f172a' }, textColor: '#94a3b8' },
          width: rsiContainerRef.current.clientWidth,
          height: 120,
          timeScale: { visible: false },
          rightPriceScale: { visible: true, borderVisible: false },
          leftPriceScale: { visible: false },
          grid: { vertLines: { visible: false, color: 'transparent' }, horzLines: { visible: false, color: 'transparent' } },
        })

        rsiChartRef.current = chart
        const series = chart.addSeries(LineSeries, { color: '#7c3aed', lastValueVisible: false })
        series.setData(rsiData)

        // Store chart and series reference for crosshair syncing
        if (chartsRef) {
          chartsRef.current.rsi = chart
          ;(chart as any).rsiSeries = series
        }

        // Subscribe to RSI crosshair moves to sync to main chart
        chart.subscribeCrosshairMove((param) => {
          if (chartsRef && chartsRef.current.mainChart) {
            const mainChart = chartsRef.current.mainChart
            if (!param.time) {
              mainChart.clearCrosshairPosition()
              return
            }
            // Just move cursor to same time - main chart will sync all indicators
            mainChart.setCrosshairPosition(0, param.time, null)
          }
        })

        const range = getVisibleRange()
        if (range) {
          chart.timeScale().setVisibleRange(range)
        } else {
          chart.timeScale().fitContent()
        }
      } catch (error) {
        console.error('RSI chart error:', error)
      }
    }

    const setupMACD = async () => {
      if (!selectedIndicators.has('MACD') || !macdContainerRef.current) return

      try {
        const lwc = await import('lightweight-charts')
        const { createChart, LineSeries, HistogramSeries } = lwc

        if (macdChartRef.current) {
          macdChartRef.current.remove()
        }

        const macd = calculateMACD(chartData)
        const macdData = chartData
          .map((candle, i) => ({
            time: candle.time,
            value: macd.histogram[i],
          }))
          .filter(d => d.value !== null)

        const chart = createChart(macdContainerRef.current, {
          layout: { background: { color: '#0f172a' }, textColor: '#94a3b8' },
          width: macdContainerRef.current.clientWidth,
          height: 120,
          timeScale: { visible: false },
          rightPriceScale: { visible: true, borderVisible: false },
          leftPriceScale: { visible: false },
          grid: { vertLines: { visible: false, color: 'transparent' }, horzLines: { visible: false, color: 'transparent' } },
        })

        macdChartRef.current = chart
        const series = chart.addSeries(HistogramSeries, { color: '#8b5cf6', lastValueVisible: false })
        series.setData(macdData)

        // Store chart and series reference for crosshair syncing
        if (chartsRef) {
          chartsRef.current.macd = chart
          ;(chart as any).macdSeries = series
        }

        // Subscribe to MACD crosshair moves to sync to main chart
        chart.subscribeCrosshairMove((param) => {
          if (chartsRef && chartsRef.current.mainChart) {
            const mainChart = chartsRef.current.mainChart
            if (!param.time) {
              mainChart.clearCrosshairPosition()
              return
            }
            // Just move cursor to same time - main chart will sync all indicators
            mainChart.setCrosshairPosition(0, param.time, null)
          }
        })

        const range = getVisibleRange()
        if (range) {
          chart.timeScale().setVisibleRange(range)
        } else {
          chart.timeScale().fitContent()
        }
      } catch (error) {
        console.error('MACD chart error:', error)
      }
    }

    setupRSI()
    setupMACD()
  }, [chartData, selectedIndicators])

  useEffect(() => {
    const range = getVisibleRange()
    if (!range) return

    if (rsiChartRef.current && selectedIndicators.has('RSI 14')) {
      rsiChartRef.current.timeScale().setVisibleRange(range)
    }
    if (macdChartRef.current && selectedIndicators.has('MACD')) {
      macdChartRef.current.timeScale().setVisibleRange(range)
    }
  }, [visibleWindow, chartData])

  if (selectedIndicators.size === 0) return null

  return (
    <div className="bg-slate-950 border-t border-slate-800">
      {selectedIndicators.has('RSI 14') && (
        <div className="border-b border-slate-800">
          <div className="px-4 py-2 bg-slate-900 text-xs font-bold text-slate-400">RSI 14</div>
          <div ref={rsiContainerRef} />
        </div>
      )}
      {selectedIndicators.has('MACD') && (
        <div>
          <div className="px-4 py-2 bg-slate-900 text-xs font-bold text-slate-400">MACD</div>
          <div ref={macdContainerRef} />
        </div>
      )}
    </div>
  )
}

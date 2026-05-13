import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { LineChart, Line, AreaChart, Area, BarChart, Bar, ComposedChart, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { api } from '@/services/api'
import { useBacktestRun, useBacktestDistribution } from '@/hooks/usePortfolio'
import { useBacktestWebSocket } from '@/hooks/useBacktestWebSocket'
import TradingChart from '@/components/TradingChart'
import CardChart from '@/components/CardChart'

export default function BacktestDetail() {
  const { strategy, runId, tab: tabParam } = useParams<{ strategy: string; runId: string; tab?: string }>()
  const navigate = useNavigate()
  const { data: response, isLoading, error } = useBacktestRun(strategy || '', runId || '')

  // Debug hook response
  useEffect(() => {
    console.log('useBacktestRun response:', { response, isLoading, error, has_data: !!response })
  }, [response, isLoading, error])

  // Real-time data tracking
  const [isRunning, setIsRunning] = useState(false)
  const [progress, setProgress] = useState({ current: 0, total: 0, percentage: 0 })
  const [realtimeMetrics, setRealtimeMetrics] = useState<any>(null)
  const [realtimeEquity, setRealtimeEquity] = useState<any[]>([])
  const [daysProcessed, setDaysProcessed] = useState(0)
  const [totalDays, setTotalDays] = useState(0)

  // Tab state - read from URL path param
  const [activeTab, setActiveTab] = useState<'performance' | 'distribution' | 'transactions' | 'watchlist'>('performance')
  const [transactionSort, setTransactionSort] = useState<{ key: string; direction: 'asc' | 'desc' }>({ key: 'entry_date', direction: 'desc' })
  const [selectedPosition, setSelectedPosition] = useState<any>(null)
  const [selectedDistributionBin, setSelectedDistributionBin] = useState<any>(null)
  const [tickerNames, setTickerNames] = useState<{ [key: string]: string }>({})
  const [chartPosition, setChartPosition] = useState<any>(null)
  const [watchlist, setWatchlist] = useState<any[]>([])
  const [watchlistLoading, setWatchlistLoading] = useState(false)
  const [watchlistError, setWatchlistError] = useState('')
  const [watchlistViewMode, setWatchlistViewMode] = useState<'table' | 'charts'>('table')
  const [watchlistSearch, setWatchlistSearch] = useState('')
  const [watchlistSortBy, setWatchlistSortBy] = useState('Score')
  const [watchlistCurrentPage, setWatchlistCurrentPage] = useState(1)
  const [watchlistHistorical, setWatchlistHistorical] = useState<{ [ticker: string]: any[] }>({})

  useEffect(() => {
    if (tabParam && ['performance', 'distribution', 'transactions', 'watchlist'].includes(tabParam)) {
      setActiveTab(tabParam as 'performance' | 'distribution' | 'transactions' | 'watchlist')
    }
  }, [tabParam])

  const handleTabChange = (tab: 'performance' | 'distribution' | 'transactions' | 'watchlist') => {
    navigate(`/backtests/${strategy}/${runId}/${tab}`)
  }

  const loadWatchlist = async () => {
    setWatchlistLoading(true)
    setWatchlistError('')
    try {
      // Use LIVE mode: load from strategy watchlist (no backtest_id)
      const response = await api.getBacktestWatchlist(strategy || '')
      if (response.status === 'success') {
        setWatchlist(response.data?.watchlist || [])
      } else {
        setWatchlistError(response.message || 'Failed to load watchlist')
      }
    } catch (err: any) {
      setWatchlistError(err.message || 'Failed to load watchlist')
    } finally {
      setWatchlistLoading(false)
    }
  }

  const regenerateWatchlist = async () => {
    setWatchlistLoading(true)
    setWatchlistError('')
    try {
      // Run strategy in live mode to regenerate watchlist
      const response = await api.regenerateBacktestWatchlist(strategy || '')
      if (response.status === 'success') {
        await loadWatchlist()
      } else {
        setWatchlistError(response.message || 'Failed to regenerate watchlist')
      }
    } catch (err: any) {
      setWatchlistError(err.message || 'Failed to regenerate watchlist')
    } finally {
      setWatchlistLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'watchlist') {
      loadWatchlist()
    }
  }, [activeTab, strategy, runId])

  // Calculate EMA helper
  const calculateEMA = (data: any[], period: number, key: string) => {
    const result = [...data]
    const multiplier = 2 / (period + 1)

    let ema: number | null = null
    for (let i = 0; i < result.length; i++) {
      if (result[i].close === undefined || result[i].close === null) continue

      if (ema === null) {
        // First EMA is SMA
        if (i >= period - 1) {
          let sum = 0
          for (let j = i - period + 1; j <= i; j++) {
            sum += result[j].close || 0
          }
          ema = sum / period
          result[i][key] = ema
        }
      } else {
        // Subsequent EMAs use the EMA formula
        ema = (result[i].close - ema) * multiplier + ema
        result[i][key] = ema
      }
    }

    return result
  }

  // Load historical data for watchlist charts
  useEffect(() => {
    if (watchlist.length === 0) return

    const loadHistoricalData = async () => {
      const historicalData: { [ticker: string]: any[] } = {}

      for (const item of watchlist) {
        try {
          // Load 120 days to ensure EMAs are calculated for the full 90-day display range
          const response = await fetch(`/api/v1/data/history/${item.ticker}?days=120`)
          if (response.ok) {
            const data = await response.json()
            if (data.data && Array.isArray(data.data)) {
              let allData = data.data.map((point: any) => ({
                date: point.date || new Date(point.timestamp).toISOString().split('T')[0],
                close: point.close,
                ema_20: point.ema_20,
                ema_50: point.ema_50,
              }))

              // Calculate missing EMAs
              allData = calculateEMA(allData, 20, 'ema_20')
              allData = calculateEMA(allData, 50, 'ema_50')

              // Take the last 90 days for display
              historicalData[item.ticker] = allData.slice(-90)
            }
          }
        } catch (err) {
          console.warn(`Failed to load historical data for ${item.ticker}:`, err)
        }
      }

      setWatchlistHistorical(historicalData)
    }

    loadHistoricalData()
  }, [watchlist])

  // WebSocket connection for real-time updates
  const { isConnected, lastMessage } = useBacktestWebSocket({
    backtest_id: runId || '',
    strategy_name: strategy || '',
    enabled: !!runId && !!strategy,
  })

  // Distribution data
  const { data: distributionResponse, isLoading: distLoading, error: distError } = useBacktestDistribution(strategy || '', runId || '')

  // Debug distribution response
  useEffect(() => {
    console.log('=== DISTRIBUTION DEBUG ===')
    console.log('Strategy:', strategy)
    console.log('RunId:', runId)
    console.log('Hook enabled?', !!(strategy && runId))
    console.log('Full response object:', distributionResponse)
    console.log('Is loading:', distLoading)
    console.log('Error:', distError)
    if (distributionResponse) {
      console.log('Response keys:', Object.keys(distributionResponse))
      console.log('Response status:', distributionResponse.status)
      console.log('Response.data:', distributionResponse.data)
      console.log('Response.distribution:', distributionResponse.distribution)
      console.log('Response.statistics:', distributionResponse.statistics)
    }
  }, [distributionResponse, distLoading, distError, strategy, runId])

  // Track if backtest is running based on WebSocket connection
  useEffect(() => {
    if (lastMessage) {
      if (lastMessage.type === 'backtest_complete') {
        setIsRunning(false)
        setProgress({ current: 100, total: 100, percentage: 100 })
        setRealtimeMetrics(lastMessage.data.metrics)
        setDaysProcessed(lastMessage.data.days_processed || daysProcessed)
        setTotalDays(lastMessage.data.days_processed || daysProcessed)
      } else if (lastMessage.type === 'daily_results') {
        setIsRunning(true)
        setDaysProcessed(prev => {
          const newCount = prev + 1
          const newPercentage = totalDays > 0 ? Math.round((newCount / totalDays) * 100) : Math.min((prev / Math.max(1, prev + 1)) * 100 + 5, 95)
          setProgress({
            current: newCount,
            total: totalDays,
            percentage: newPercentage,
          })
          return newCount
        })
      } else if (lastMessage.type === 'error') {
        setIsRunning(false)
      }
    }
  }, [lastMessage, totalDays])

  // Fetch portfolio history with evolving metrics - only while running
  useEffect(() => {
    if (!strategy || !runId || !isRunning) return

    const fetchInterval = setInterval(async () => {
      try {
        const historyRes = await fetch(`/api/v1/backtests/${strategy}/${runId}/history`)
        if (historyRes.status === 200) {
          const historyData = await historyRes.json()
          if (historyData.status === 'success' && historyData.history) {
            const equityCurve = historyData.history.map((h: any) => ({
              date: h.date,
              value: h.value,
              drawdown_pct: h.drawdown_pct,
            }))
            setRealtimeEquity(equityCurve)

            const latest = historyData.history[historyData.history.length - 1]
            if (latest) {
              setRealtimeMetrics({
                total_return_pct: latest.return_pct,
                max_drawdown_pct: historyData.max_drawdown_pct ?? (Math.min(...historyData.history.map((h: any) => h.drawdown_pct)) || 0),
              })
            }

            if (historyData.history.length > 0) {
              setDaysProcessed(historyData.history.length)
            }
          }
        }
      } catch (e) {
        // Silently fail
      }
    }, 1000)

    return () => clearInterval(fetchInterval)
  }, [strategy, runId, isRunning])

  // response has { status, data }, we need the inner data object
  const backtest = response?.data
  const hasData = backtest && (backtest.equity_curve?.length > 0 || Object.keys(backtest.portfolio_metrics || {}).length > 0)

  // Fetch ticker names from distribution data
  useEffect(() => {
    if (distributionResponse?.data?.trades) {
      const uniqueTickers = new Set<string>()
      distributionResponse.data.trades.forEach((trade: any) => {
        uniqueTickers.add(trade.ticker)
      })

      const fetchCompanyNames = async () => {
        const names: { [key: string]: string } = {}

        for (const ticker of uniqueTickers) {
          try {
            const response = await api.getFundamental(ticker)
            names[ticker] = response.data?.company?.name || ticker
          } catch (err) {
            console.error(`Failed to fetch name for ${ticker}:`, err)
            names[ticker] = ticker
          }
        }

        setTickerNames(names)
      }

      fetchCompanyNames()
    }
  }, [distributionResponse])

  // Debug logging
  useEffect(() => {
    if (backtest) {
      console.log('Backtest data loaded:', {
        has_portfolio_metrics: !!backtest.portfolio_metrics,
        portfolio_metrics_keys: backtest.portfolio_metrics ? Object.keys(backtest.portfolio_metrics) : [],
        total_return_pct: backtest.total_return_pct,
        max_drawdown_pct: backtest.max_drawdown_pct,
        sharpe_ratio: backtest.sharpe_ratio,
      })
    }
  }, [backtest])

  if (isLoading && !hasData && !isConnected) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4">
          <div className="flex items-center justify-center w-16 h-16 rounded-full border-4 border-slate-700 border-t-purple-600 animate-spin mx-auto" />
          <p className="text-slate-400">Loading backtest details...</p>
        </div>
      </div>
    )
  }

  if (!backtest && !isConnected) {
    return (
      <div className="text-center space-y-4 py-12">
        <p className="text-red-400 text-lg">Backtest not found</p>
        <Link to="/backtests" className="text-purple-400 hover:text-purple-300">← Back to Runs</Link>
      </div>
    )
  }

  if (!backtest && isConnected) {
    return (
      <div className="space-y-6">
        <div className="flex items-baseline justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">{strategy}</h1>
            <p className="text-xs text-slate-500 font-mono">{runId}</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="px-3 py-1 bg-blue-900/30 border border-blue-800 rounded text-blue-400 text-xs font-medium">
              🔄 Running
            </div>
            <Link to="/backtests" className="text-slate-400 hover:text-slate-300 text-xs">
              Back
            </Link>
          </div>
        </div>

        <div className="space-y-2">
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700">
            <div
              className="h-full bg-gradient-to-r from-purple-600 to-violet-600 transition-all duration-300"
              style={{ width: `${progress.percentage}%` }}
            />
          </div>
          <div className="text-center text-slate-400 text-xs">
            {Math.round(progress.percentage)}% {daysProcessed > 0 && totalDays > 0 && `(${daysProcessed}/${totalDays})`}
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div className="bg-slate-800/50 rounded p-4 border border-slate-700">
            <div className="text-slate-500 text-xs mb-1">Return</div>
            <div className={`text-2xl font-bold ${
              (realtimeMetrics?.total_return_pct || 0) >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {(realtimeMetrics?.total_return_pct || 0).toFixed(1)}%
            </div>
          </div>
          <div className="bg-slate-800/50 rounded p-4 border border-slate-700">
            <div className="text-slate-500 text-xs mb-1">Drawdown</div>
            <div className="text-2xl font-bold text-red-400">
              {(realtimeMetrics?.max_drawdown_pct || 0).toFixed(1)}%
            </div>
          </div>
          <div className="bg-slate-800/50 rounded p-4 border border-slate-700">
            <div className="text-slate-500 text-xs mb-1">Days</div>
            <div className="text-2xl font-bold text-white">{daysProcessed}</div>
          </div>
        </div>

        {realtimeEquity.length > 0 && (
          <div className="bg-slate-900/50 rounded p-6 border border-slate-800">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={realtimeEquity} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                  <XAxis dataKey="date" stroke="#94a3b8" style={{ fontSize: '11px' }} />
                  <YAxis stroke="#94a3b8" style={{ fontSize: '11px' }} />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '6px' }} />
                  <Line type="monotone" dataKey="value" stroke="#a78bfa" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    )
  }

  // Use real-time metrics first, then portfolio_metrics, then fallback to top-level metrics from API
  // Build metrics from available sources
  const metrics = realtimeMetrics ||
    (backtest?.portfolio_metrics && Object.keys(backtest.portfolio_metrics).length > 0 ? backtest.portfolio_metrics : null) ||
    {
      total_return_pct: backtest?.total_return_pct ?? 0,
      sharpe_ratio: backtest?.sharpe_ratio ?? 0,
      sortino_ratio: backtest?.sortino_ratio ?? 0,
      max_drawdown_pct: backtest?.max_drawdown_pct ?? 0,
      calmar_ratio: backtest?.calmar_ratio ?? 0,
      win_rate_pct: backtest?.win_rate_pct ?? 0,
      profit_factor: backtest?.profit_factor ?? 0,
      total_trades: backtest?.total_trades ?? 0,
      avg_winning_trade_pct: backtest?.avg_winning_trade_pct ?? 0,
      avg_losing_trade_pct: backtest?.avg_losing_trade_pct ?? 0,
      best_trade_pct: backtest?.best_trade_pct ?? 0,
      worst_trade_pct: backtest?.worst_trade_pct ?? 0,
    }
  const baseEquity = realtimeEquity.length > 0 ? realtimeEquity : (backtest?.equity_curve || [])

  // Ensure equity data includes drawdown
  const equity = baseEquity.map((point: any, idx: number) => {
    if ('drawdown_pct' in point && point.drawdown_pct !== null) {
      return point
    }
    const peak = Math.max(...baseEquity.slice(0, idx + 1).map((p: any) => p.value))
    const drawdown = ((point.value - peak) / peak) * 100
    return { ...point, drawdown_pct: drawdown }
  })

  const MetricRow = ({ label, value, color = 'text-white' }: { label: string; value: string | number; color?: string }) => (
    <div className="flex items-start justify-between py-3 border-b border-slate-800 last:border-b-0">
      <span className="text-slate-400 text-sm">{label}</span>
      <span className={`font-bold text-sm ${color}`}>{value}</span>
    </div>
  )

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{strategy}</h1>
          <p className="text-xs text-slate-500 font-mono">{runId}</p>
        </div>
        <div className="flex items-center gap-3">
          {isRunning && (
            <div className="px-3 py-1 bg-blue-900/30 border border-blue-800 rounded text-blue-400 text-xs font-medium">
              🔄 Running
            </div>
          )}
          <button
            onClick={() => navigate(`/backtests/compare?items=${strategy}:${runId}`)}
            className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-white rounded text-xs font-medium transition"
          >
            Compare
          </button>
          <Link to="/backtests" className="text-slate-400 hover:text-slate-300 text-xs">
            Back
          </Link>
        </div>
      </div>

      {/* Progress Bar */}
      {isRunning && (
        <div className="space-y-2">
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700">
            <div
              className="h-full bg-gradient-to-r from-purple-600 to-violet-600 transition-all duration-300"
              style={{ width: `${progress.percentage}%` }}
            />
          </div>
          <div className="text-center text-slate-400 text-xs">
            {Math.round(progress.percentage)}% {daysProcessed > 0 && totalDays > 0 && `(${daysProcessed}/${totalDays} days)`}
          </div>
        </div>
      )}

      {/* Main Tab Navigation */}
      <div className="flex gap-1 border-b border-slate-700">
        <button
          onClick={() => handleTabChange('performance')}
          className={`px-4 py-2 text-sm font-medium transition ${
            activeTab === 'performance'
              ? 'text-purple-400 border-b-2 border-purple-400'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          Performance
        </button>
        <button
          onClick={() => handleTabChange('transactions')}
          className={`px-4 py-2 text-sm font-medium transition ${
            activeTab === 'transactions'
              ? 'text-purple-400 border-b-2 border-purple-400'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          Transactions
        </button>
        <button
          onClick={() => handleTabChange('watchlist')}
          className={`px-4 py-2 text-sm font-medium transition ${
            activeTab === 'watchlist'
              ? 'text-purple-400 border-b-2 border-purple-400'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          Watchlist
        </button>
      </div>

      {/* Performance Section - Only show when on performance tab */}
      {activeTab === 'performance' && (
        <div className="space-y-4">
          <div className="grid grid-cols-12 gap-4">
            {/* Charts - Left Side (9 cols) */}
            <div className="col-span-9 space-y-4">
          {/* Equity Curve */}
          <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 shadow-lg">
            <h2 className="text-sm font-bold text-white mb-4">EQUITY CURVE</h2>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={equity} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                  <XAxis dataKey="date" stroke="#94a3b8" style={{ fontSize: '11px' }} />
                  <YAxis stroke="#94a3b8" style={{ fontSize: '11px' }} />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }} />
                  <Line type="monotone" dataKey="value" stroke="#a78bfa" strokeWidth={2.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Drawdown */}
          <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 shadow-lg">
            <h2 className="text-sm font-bold text-white mb-4">DRAWDOWN</h2>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={equity} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                  <XAxis dataKey="date" stroke="#94a3b8" style={{ fontSize: '11px' }} />
                  <YAxis stroke="#94a3b8" style={{ fontSize: '11px' }} label={{ value: '%', angle: -90, position: 'insideLeft' }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                    formatter={(value: any) => [(value as number).toFixed(2) + '%', 'Drawdown']}
                  />
                  <Area
                    type="monotone"
                    dataKey="drawdown_pct"
                    fill="#ef4444"
                    stroke="#dc2626"
                    fillOpacity={0.3}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
            </div>

            {/* Metrics - Right Side (3 cols) */}
            <div className="col-span-3">
          <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 shadow-lg sticky top-0">
            <h2 className="text-sm font-bold text-white mb-4">KEY METRICS</h2>
            <div className="space-y-0">
              <MetricRow
                label="Total Return"
                value={`${(metrics.total_return_pct || 0).toFixed(2)}%`}
                color={(metrics.total_return_pct || 0) >= 0 ? 'text-green-400' : 'text-red-400'}
              />
              <MetricRow
                label="Sharpe Ratio"
                value={`${(metrics.sharpe_ratio || 0).toFixed(2)}`}
                color="text-purple-400"
              />
              <MetricRow
                label="Sortino Ratio"
                value={`${(metrics.sortino_ratio || 0).toFixed(2)}`}
                color="text-purple-400"
              />
              <MetricRow
                label="Max Drawdown"
                value={`${(metrics.max_drawdown_pct || 0).toFixed(2)}%`}
                color="text-red-400"
              />
              <MetricRow
                label="Calmar Ratio"
                value={`${(metrics.calmar_ratio || 0).toFixed(2)}`}
              />
              <MetricRow
                label="Win Rate"
                value={`${(metrics.win_rate_pct || 0).toFixed(1)}%`}
                color="text-green-400"
              />
              <MetricRow
                label="Profit Factor"
                value={`${(metrics.profit_factor || 0).toFixed(2)}`}
              />
              <MetricRow
                label="Total Trades"
                value={metrics.total_trades || 0}
              />
              <MetricRow
                label="Avg Win Trade"
                value={`${(metrics.avg_winning_trade_pct || 0).toFixed(2)}%`}
                color="text-green-400"
              />
              <MetricRow
                label="Avg Loss Trade"
                value={`${(metrics.avg_losing_trade_pct || 0).toFixed(2)}%`}
                color="text-red-400"
              />
              <MetricRow
                label="Best Trade"
                value={`${(metrics.best_trade_pct || 0).toFixed(2)}%`}
                color="text-green-400"
              />
              <MetricRow
                label="Worst Trade"
                value={`${(metrics.worst_trade_pct || 0).toFixed(2)}%`}
                color="text-red-400"
              />
            </div>
            </div>
            </div>
          </div>

          {/* Distribution Section */}
          <div>
            <h2 className="text-lg font-bold text-white mb-4">RETURN DISTRIBUTION (4% STEPS)</h2>
              {distLoading ? (
              <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 text-center text-slate-400">
                Loading distribution data...
              </div>
            ) : distError ? (
              <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 text-center">
                <p className="text-red-400 mb-2">Error loading distribution</p>
                <p className="text-xs text-slate-400">{(distError as any)?.message}</p>
              </div>
            ) : distributionResponse?.status === 'success' ? (
              <>
                {(() => {
                  // Handle both flat and nested response structures
                  const distData = distributionResponse.data || distributionResponse
                  const distStats = distData.statistics || {}
                  const distribution = distData.distribution || []

                  return (
                    <div className="grid grid-cols-12 gap-4">
                      {/* Distribution Chart - Left Side (9 cols) */}
                      <div className="col-span-9">
                      <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 shadow-lg">
                        <h2 className="text-sm font-bold text-white mb-4">RETURN DISTRIBUTION (4% STEPS)</h2>
                        <div className="h-80">
                          <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart
                              data={distribution}
                              margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
                            >
                              <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                              <XAxis dataKey="return_range" stroke="#94a3b8" style={{ fontSize: '11px' }} angle={-45} textAnchor="end" height={80} label={{ value: 'Return %', position: 'insideBottom', offset: -10 }} />
                              <YAxis yAxisId="left" stroke="#94a3b8" style={{ fontSize: '11px' }} label={{ value: 'Frequency (Trades)', angle: -90, position: 'insideLeft' }} />
                              <YAxis yAxisId="right" orientation="right" stroke="#94a3b8" style={{ fontSize: '11px' }} label={{ value: 'Cumulative P&L ($)', angle: 90, position: 'insideRight' }} />
                              <Tooltip
                                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                                formatter={(value: any) => {
                                  if (typeof value === 'number') {
                                    if (Math.abs(value) > 1000) {
                                      return `$${(value / 1000).toFixed(1)}k`
                                    }
                                    return `${Math.round(value)}`
                                  }
                                  return value
                                }}
                              />
                              <Legend />
                              <Bar yAxisId="left" dataKey="trade_count" fill="#a78bfa" name="Frequency" />
                              <Line yAxisId="right" type="monotone" dataKey="cumulative_pnl_total" stroke="#10b981" strokeWidth={2} name="Cumulative P&L" />
                            </ComposedChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                    </div>

                    {/* Distribution Stats - Right Side (3 cols) */}
                    <div className="col-span-3">
                      <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 shadow-lg sticky top-0">
                        <h2 className="text-sm font-bold text-white mb-4">DISTRIBUTION STATS</h2>
                        <div className="space-y-0">
                          <MetricRow
                            label="Total Trades"
                            value={distStats.total_trades || 0}
                          />
                          <MetricRow
                            label="Total P&L"
                            value={`$${(distStats.total_pnl || 0).toFixed(0)}`}
                            color={(distStats.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}
                          />
                          <MetricRow
                            label="Win Rate"
                            value={`${(distStats.win_rate || 0).toFixed(1)}%`}
                            color="text-green-400"
                          />
                          <MetricRow
                            label="Avg Return"
                            value={`${(distStats.avg_return || 0).toFixed(2)}%`}
                            color={(distStats.avg_return || 0) >= 0 ? 'text-green-400' : 'text-red-400'}
                          />
                          <MetricRow
                            label="Median Return"
                            value={`${(distStats.median_return || 0).toFixed(2)}%`}
                            color={(distStats.median_return || 0) >= 0 ? 'text-green-400' : 'text-red-400'}
                          />
                          <MetricRow
                            label="Min Return"
                            value={`${(distStats.min_return || 0).toFixed(2)}%`}
                            color="text-red-400"
                          />
                          <MetricRow
                            label="Max Return"
                            value={`${(distStats.max_return || 0).toFixed(2)}%`}
                            color="text-green-400"
                          />
                          <MetricRow
                            label="Std Dev"
                            value={`${(distStats.std_return || 0).toFixed(2)}%`}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                  )
                })()}
              </>
            ) : (
              <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 text-center text-slate-400">
                No distribution data available
              </div>
            )}
            </div>
          </div>
      )}

      {/* Transactions Tab */}
      {activeTab === 'transactions' && (
        <>
          {/* Distribution Section */}
          <div className="space-y-4 mb-6">
            <div>
              <h2 className="text-lg font-bold text-white mb-4">RETURN DISTRIBUTION (4% STEPS)</h2>
              {distLoading ? (
                  <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 text-center text-slate-400">
                    Loading distribution data...
                  </div>
                ) : distError ? (
                  <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 text-center">
                    <p className="text-red-400 mb-2">Error loading distribution</p>
                    <p className="text-xs text-slate-400">{(distError as any)?.message}</p>
                  </div>
                ) : distributionResponse?.status === 'success' ? (
                  <>
                    {(() => {
                      // Handle both flat and nested response structures
                      const distData = distributionResponse.data || distributionResponse
                      const distStats = distData.statistics || {}
                      const distribution = distData.distribution || []

                      return (
                        <div className="grid grid-cols-12 gap-4">
                          {/* Distribution Chart - Left Side (9 cols) */}
                          <div className="col-span-9">
                            <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 shadow-lg">
                              <div className="h-80">
                                <ResponsiveContainer width="100%" height="100%">
                                  <ComposedChart
                                    data={distribution}
                                    margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
                                  >
                                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                                    <XAxis dataKey="return_range" stroke="#94a3b8" style={{ fontSize: '11px' }} angle={-45} textAnchor="end" height={80} label={{ value: 'Return %', position: 'insideBottom', offset: -10 }} />
                                    <YAxis yAxisId="left" stroke="#94a3b8" style={{ fontSize: '11px' }} label={{ value: 'Frequency (Trades)', angle: -90, position: 'insideLeft' }} />
                                    <YAxis yAxisId="right" orientation="right" stroke="#94a3b8" style={{ fontSize: '11px' }} label={{ value: 'Cumulative P&L ($)', angle: 90, position: 'insideRight' }} />
                                    <Tooltip
                                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                                      formatter={(value: any) => {
                                        if (typeof value === 'number') {
                                          if (Math.abs(value) > 1000) {
                                            return `$${(value / 1000).toFixed(1)}k`
                                          }
                                          return `${Math.round(value)}`
                                        }
                                        return value
                                      }}
                                    />
                                    <Legend />
                                    <Bar
                                      yAxisId="left"
                                      dataKey="trade_count"
                                      fill="#a78bfa"
                                      name="Frequency"
                                      onClick={(data: any) => setSelectedDistributionBin(data)}
                                      style={{ cursor: 'pointer' }}
                                    />
                                    <Line yAxisId="right" type="monotone" dataKey="cumulative_pnl_total" stroke="#10b981" strokeWidth={2} name="Cumulative P&L" />
                                  </ComposedChart>
                                </ResponsiveContainer>
                              </div>
                            </div>
                          </div>

                          {/* Distribution Stats - Right Side (3 cols) */}
                          <div className="col-span-3">
                            <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 shadow-lg sticky top-0">
                              <h2 className="text-sm font-bold text-white mb-4">DISTRIBUTION STATS</h2>
                              <div className="space-y-0">
                                <MetricRow
                                  label="Total Trades"
                                  value={distStats.total_trades || 0}
                                />
                                <MetricRow
                                  label="Total P&L"
                                  value={`$${(distStats.total_pnl || 0).toFixed(0)}`}
                                  color={(distStats.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}
                                />
                                <MetricRow
                                  label="Win Rate"
                                  value={`${(distStats.win_rate || 0).toFixed(1)}%`}
                                  color="text-green-400"
                                />
                                <MetricRow
                                  label="Avg Return"
                                  value={`${(distStats.avg_return || 0).toFixed(2)}%`}
                                  color={(distStats.avg_return || 0) >= 0 ? 'text-green-400' : 'text-red-400'}
                                />
                                <MetricRow
                                  label="Median Return"
                                  value={`${(distStats.median_return || 0).toFixed(2)}%`}
                                  color={(distStats.median_return || 0) >= 0 ? 'text-green-400' : 'text-red-400'}
                                />
                                <MetricRow
                                  label="Min Return"
                                  value={`${(distStats.min_return || 0).toFixed(2)}%`}
                                  color="text-red-400"
                                />
                                <MetricRow
                                  label="Max Return"
                                  value={`${(distStats.max_return || 0).toFixed(2)}%`}
                                  color="text-green-400"
                                />
                                <MetricRow
                                  label="Std Dev"
                                  value={`${(distStats.std_return || 0).toFixed(2)}%`}
                                />
                              </div>
                            </div>
                          </div>
                        </div>
                      )
                    })()}
                  </>
                ) : (
                  <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 text-center text-slate-400">
                    No distribution data available
                  </div>
                )}
            </div>
          </div>

          {/* Closed Positions List Section */}
          {(distributionResponse?.data?.trades || distributionResponse?.trades) && (distributionResponse?.data?.trades || distributionResponse?.trades).length > 0 ? (
            <div className="grid grid-cols-12 gap-4">
              {/* Positions Table - Left Side (9 cols) */}
              <div className="col-span-9">
                <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 shadow-lg">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-white">CLOSED POSITIONS</h3>
                    {selectedDistributionBin && (
                      <div className="text-xs bg-purple-600/20 border border-purple-600/50 text-purple-300 px-3 py-1 rounded">
                        Showing {selectedDistributionBin.return_range}
                      </div>
                    )}
                  </div>
                  {(() => {
                    // Calculate positions outside table for use in footer too
                    const distData = distributionResponse?.data || distributionResponse
                    const apiTrades = distData?.trades || []

                    let positions: any[] = []

                    if (apiTrades.length > 0) {
                      positions = apiTrades.map((trade: any, idx: number) => ({
                        entry_date: trade.entry_date,
                        exit_date: trade.exit_date,
                        ticker: trade.ticker,
                        quantity: trade.quantity,
                        entry_price: trade.entry_price || (trade.cost_basis / trade.quantity),
                        exit_price: 0,
                        pnl: trade.pnl,
                        return_pct: trade.return_pct,
                        close_reason: trade.return_pct >= 5 ? '✅ Target' : trade.return_pct <= -2 ? '⛔ Stop Loss' : 'Sold',
                        entry_metadata: trade.entry_metadata,
                        exit_metadata: trade.exit_metadata,
                        sortKey: idx
                      })).map((pos: any) => ({
                        ...pos,
                        exit_price: pos.entry_price + (pos.pnl / pos.quantity)
                      }))
                    } else {
                      let buys: any = {}
                      trades.forEach((trade: any) => {
                        if (trade.operation === 'BUY') {
                          if (!buys[trade.ticker]) buys[trade.ticker] = []
                          buys[trade.ticker].push({
                            date: trade.created_at,
                            quantity: trade.quantity,
                            price: trade.price,
                            fees: trade.fees || 0,
                            metadata: trade.metadata || ''
                          })
                        } else if (trade.operation === 'SELL' && buys[trade.ticker] && buys[trade.ticker].length > 0) {
                          let remainingQty = trade.quantity
                          while (remainingQty > 0 && buys[trade.ticker].length > 0) {
                            const buy = buys[trade.ticker].shift()
                            const matchedQty = Math.min(remainingQty, buy.quantity)
                            const grossPnL = matchedQty * (trade.price - buy.price)
                            const buyFeesPortion = buy.fees * (matchedQty / buy.quantity)
                            const sellFeesPortion = (trade.fees || 0) * (matchedQty / trade.quantity)
                            const netPnL = grossPnL - buyFeesPortion - sellFeesPortion
                            const costBasis = matchedQty * buy.price + buyFeesPortion
                            const returnPct = costBasis !== 0 ? (netPnL / costBasis) * 100 : 0
                            positions.push({
                              entry_date: buy.date,
                              exit_date: trade.created_at,
                              ticker: trade.ticker,
                              quantity: matchedQty,
                              entry_price: buy.price,
                              exit_price: trade.price,
                              pnl: netPnL,
                              return_pct: returnPct,
                              close_reason: returnPct >= 5 ? '✅ Target' : returnPct <= -2 ? '⛔ Stop Loss' : 'Sold',
                              entry_metadata: buy.metadata,
                              exit_metadata: trade.metadata || '',
                              sortKey: positions.length
                            })
                            remainingQty -= matchedQty
                          }
                        }
                      })
                    }

                    // Filter by selected distribution bin
                    const filteredPositions = selectedDistributionBin
                      ? positions.filter((pos: any) =>
                          pos.return_pct >= selectedDistributionBin.return_min &&
                          pos.return_pct <= selectedDistributionBin.return_max
                        )
                      : positions

                    return (
                      <>
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs">
                            <thead className="border-b border-slate-700">
                              <tr className="text-slate-500">
                                <th className="text-left py-2 px-2 cursor-pointer hover:text-slate-400" onClick={() => setTransactionSort({ key: 'entry_date', direction: transactionSort.direction === 'desc' ? 'asc' : 'desc' })}>
                                  Entry Date {transactionSort.key === 'entry_date' && (transactionSort.direction === 'desc' ? '↓' : '↑')}
                                </th>
                                <th className="text-left py-2 px-2 cursor-pointer hover:text-slate-400" onClick={() => setTransactionSort({ key: 'exit_date', direction: transactionSort.direction === 'desc' ? 'asc' : 'desc' })}>
                                  Exit Date {transactionSort.key === 'exit_date' && (transactionSort.direction === 'desc' ? '↓' : '↑')}
                                </th>
                                <th className="text-left py-2 px-2 cursor-pointer hover:text-slate-400" onClick={() => setTransactionSort({ key: 'ticker', direction: transactionSort.key === 'ticker' && transactionSort.direction === 'desc' ? 'asc' : 'desc' })}>
                                  Ticker {transactionSort.key === 'ticker' && (transactionSort.direction === 'desc' ? '↓' : '↑')}
                                </th>
                                <th className="text-left py-2 px-2">Name</th>
                                <th className="text-right py-2 px-2 cursor-pointer hover:text-slate-400" onClick={() => setTransactionSort({ key: 'quantity', direction: transactionSort.key === 'quantity' && transactionSort.direction === 'desc' ? 'asc' : 'desc' })}>
                                  Qty {transactionSort.key === 'quantity' && (transactionSort.direction === 'desc' ? '↓' : '↑')}
                                </th>
                                <th className="text-right py-2 px-2 cursor-pointer hover:text-slate-400" onClick={() => setTransactionSort({ key: 'entry_price', direction: transactionSort.key === 'entry_price' && transactionSort.direction === 'desc' ? 'asc' : 'desc' })}>
                                  Entry {transactionSort.key === 'entry_price' && (transactionSort.direction === 'desc' ? '↓' : '↑')}
                                </th>
                                <th className="text-right py-2 px-2 cursor-pointer hover:text-slate-400" onClick={() => setTransactionSort({ key: 'exit_price', direction: transactionSort.key === 'exit_price' && transactionSort.direction === 'desc' ? 'asc' : 'desc' })}>
                                  Exit {transactionSort.key === 'exit_price' && (transactionSort.direction === 'desc' ? '↓' : '↑')}
                                </th>
                                <th className="text-right py-2 px-2 cursor-pointer hover:text-slate-400" onClick={() => setTransactionSort({ key: 'pnl', direction: transactionSort.key === 'pnl' && transactionSort.direction === 'desc' ? 'asc' : 'desc' })}>
                                  P&L $ {transactionSort.key === 'pnl' && (transactionSort.direction === 'desc' ? '↓' : '↑')}
                                </th>
                                <th className="text-right py-2 px-2 cursor-pointer hover:text-slate-400" onClick={() => setTransactionSort({ key: 'return_pct', direction: transactionSort.key === 'return_pct' && transactionSort.direction === 'desc' ? 'asc' : 'desc' })}>
                                  Return % {transactionSort.key === 'return_pct' && (transactionSort.direction === 'desc' ? '↓' : '↑')}
                                </th>
                                <th className="text-left py-2 px-2 cursor-pointer hover:text-slate-400" onClick={() => setTransactionSort({ key: 'close_reason', direction: transactionSort.key === 'close_reason' && transactionSort.direction === 'desc' ? 'asc' : 'desc' })}>
                                  Close Reason {transactionSort.key === 'close_reason' && (transactionSort.direction === 'desc' ? '↓' : '↑')}
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {(() => {
                                // Sort positions
                                filteredPositions.sort((a: any, b: any) => {
                                  let aVal: any = a[transactionSort.key]
                                  let bVal: any = b[transactionSort.key]

                                  if (transactionSort.key === 'entry_date') {
                                    try {
                                      const aMetadata = typeof a.entry_metadata === 'string' ? JSON.parse(a.entry_metadata) : a.entry_metadata
                                      const bMetadata = typeof b.entry_metadata === 'string' ? JSON.parse(b.entry_metadata) : b.entry_metadata
                                      aVal = new Date(aMetadata?.timestamp || a.entry_date).getTime()
                                      bVal = new Date(bMetadata?.timestamp || b.entry_date).getTime()
                                    } catch {
                                      aVal = new Date(aVal).getTime()
                                      bVal = new Date(bVal).getTime()
                                    }
                                  } else if (transactionSort.key === 'exit_date') {
                                    try {
                                      const aMetadata = typeof a.exit_metadata === 'string' ? JSON.parse(a.exit_metadata) : a.exit_metadata
                                      const bMetadata = typeof b.exit_metadata === 'string' ? JSON.parse(b.exit_metadata) : b.exit_metadata
                                      aVal = new Date(aMetadata?.timestamp || a.exit_date).getTime()
                                      bVal = new Date(bMetadata?.timestamp || b.exit_date).getTime()
                                    } catch {
                                      aVal = new Date(aVal).getTime()
                                      bVal = new Date(bVal).getTime()
                                    }
                                  } else if (typeof aVal === 'string') {
                                    aVal = aVal.toLowerCase()
                                    bVal = bVal.toLowerCase()
                                  }

                                  if (transactionSort.direction === 'asc') {
                                    return aVal > bVal ? 1 : aVal < bVal ? -1 : 0
                                  } else {
                                    return aVal < bVal ? 1 : aVal > bVal ? -1 : 0
                                  }
                                })

                                return filteredPositions.length > 0 ? filteredPositions.map((pos: any) => (
                                  <tr key={pos.sortKey} onClick={() => setSelectedPosition(pos)} className={`border-b border-slate-800 cursor-pointer transition ${selectedPosition?.sortKey === pos.sortKey ? 'bg-purple-600/20' : 'hover:bg-slate-800/30'}`}>
                                    <td className="py-2 px-2 text-slate-400">
                                      {(() => {
                                        try {
                                          const entryMeta = typeof pos.entry_metadata === 'string' ? JSON.parse(pos.entry_metadata) : pos.entry_metadata
                                          return new Date(entryMeta.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' })
                                        } catch {
                                          return pos.entry_date ? new Date(pos.entry_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' }) : '-'
                                        }
                                      })()}
                                    </td>
                                    <td className="py-2 px-2 text-slate-400">
                                      {(() => {
                                        try {
                                          const exitMeta = typeof pos.exit_metadata === 'string' ? JSON.parse(pos.exit_metadata) : pos.exit_metadata
                                          return new Date(exitMeta.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' })
                                        } catch {
                                          return pos.exit_date ? new Date(pos.exit_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' }) : '-'
                                        }
                                      })()}
                                    </td>
                                    <td className="py-2 px-2 text-white font-medium">{pos.ticker}</td>
                                    <td className="py-2 px-2 text-slate-400 text-sm">{tickerNames[pos.ticker] || '—'}</td>
                                    <td className="py-2 px-2 text-right text-white">{pos.quantity}</td>
                                    <td className="py-2 px-2 text-right text-slate-400">${pos.entry_price.toFixed(2)}</td>
                                    <td className="py-2 px-2 text-right text-slate-400">${pos.exit_price.toFixed(2)}</td>
                                    <td className={`py-2 px-2 text-right font-bold ${pos.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                      ${pos.pnl.toFixed(2)}
                                    </td>
                                    <td className={`py-2 px-2 text-right font-bold ${pos.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                      {pos.return_pct.toFixed(2)}%
                                    </td>
                                    <td className="py-2 px-2 text-left text-slate-300">{pos.close_reason}</td>
                                    <td className="py-2 px-2 text-center">
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation()
                                          console.log('Position object:', pos)
                                          console.log('Position keys:', Object.keys(pos))
                                          console.log('entry_date:', pos.entry_date)
                                          console.log('exit_date:', pos.exit_date)
                                          setChartPosition(pos)
                                        }}
                                        className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition whitespace-nowrap"
                                        title="View price chart"
                                      >
                                        Chart
                                      </button>
                                    </td>
                                  </tr>
                                )) : (
                                  <tr>
                                    <td colSpan={9} className="py-4 text-center text-slate-400">
                                      {selectedDistributionBin ? `No positions in ${selectedDistributionBin.return_range} range` : 'No closed positions yet'}
                                    </td>
                                  </tr>
                                )
                              })()}
                            </tbody>
                          </table>
                        </div>
                        <div className="mt-4 pt-4 border-t border-slate-700">
                          <div className="flex items-center justify-between">
                            <p className="text-sm text-slate-400">
                              {selectedDistributionBin ? (
                                <>Filtered: <span className="text-white font-semibold">{filteredPositions?.length || 0}</span> of <span className="text-white font-semibold">{apiTrades?.length || 0}</span></>
                              ) : (
                                <>Total Closed Positions: <span className="text-white font-semibold">{apiTrades?.length || 0}</span></>
                              )}
                            </p>
                            {selectedDistributionBin && (
                              <button
                                onClick={() => setSelectedDistributionBin(null)}
                                className="text-xs text-slate-400 hover:text-slate-300 px-2 py-1 rounded border border-slate-600 hover:border-slate-500 transition"
                              >
                                Clear filter
                              </button>
                            )}
                          </div>
                        </div>
                      </>
                    )
                  })()}
                </div>
              </div>

              {/* Detail Panel - Right Side (3 cols) */}
              {selectedPosition && (
                <div className="col-span-3 h-fit sticky top-6">
                  <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 shadow-lg">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-sm font-bold text-white">POSITION INDICATORS</h3>
                      <button onClick={() => setSelectedPosition(null)} className="text-slate-500 hover:text-slate-300 text-lg">✕</button>
                    </div>

                    <div className="space-y-4">
                      {/* Entry Indicators */}
                      {selectedPosition.entry_metadata && (
                        <div>
                          <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">📈 Entry Indicators</div>
                          <div className="bg-slate-800/30 rounded p-3 max-h-80 overflow-y-auto">
                            {(() => {
                              try {
                                const data = typeof selectedPosition.entry_metadata === 'string'
                                  ? JSON.parse(selectedPosition.entry_metadata)
                                  : selectedPosition.entry_metadata

                                // Separate OHLCV and indicators
                                const ohlcv = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'ticker']
                                const indicators = Object.entries(data)
                                  .filter(([k]) => !ohlcv.includes(k))
                                  .sort(([a], [b]) => a.localeCompare(b))

                                return (
                                  <div className="space-y-3 text-xs">
                                    {data.timestamp && (
                                      <div className="pb-2 border-b border-slate-700">
                                        <div className="text-slate-400">{new Date(data.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit', hour: '2-digit', minute: '2-digit' })}</div>
                                      </div>
                                    )}
                                    <div className="grid grid-cols-2 gap-2">
                                      {indicators.map(([key, value]: [string, any]) => (
                                        <div key={key} className="flex justify-between">
                                          <span className="text-slate-400">{key}</span>
                                          <span className="text-slate-200 font-mono">{typeof value === 'number' ? value.toFixed(2) : value}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )
                              } catch (e) {
                                return <div className="text-slate-300 text-xs whitespace-pre-wrap">{selectedPosition.entry_metadata}</div>
                              }
                            })()}
                          </div>
                        </div>
                      )}

                      {/* Exit Indicators */}
                      {selectedPosition.exit_metadata && (
                        <div>
                          <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">📉 Exit Indicators</div>
                          <div className="bg-slate-800/30 rounded p-3 max-h-80 overflow-y-auto">
                            {(() => {
                              try {
                                const data = typeof selectedPosition.exit_metadata === 'string'
                                  ? JSON.parse(selectedPosition.exit_metadata)
                                  : selectedPosition.exit_metadata

                                // Separate OHLCV and indicators
                                const ohlcv = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'ticker']
                                const indicators = Object.entries(data)
                                  .filter(([k]) => !ohlcv.includes(k))
                                  .sort(([a], [b]) => a.localeCompare(b))

                                return (
                                  <div className="space-y-3 text-xs">
                                    {data.timestamp && (
                                      <div className="pb-2 border-b border-slate-700">
                                        <div className="text-slate-400">{new Date(data.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit', hour: '2-digit', minute: '2-digit' })}</div>
                                      </div>
                                    )}
                                    <div className="grid grid-cols-2 gap-2">
                                      {indicators.map(([key, value]: [string, any]) => (
                                        <div key={key} className="flex justify-between">
                                          <span className="text-slate-400">{key}</span>
                                          <span className="text-slate-200 font-mono">{typeof value === 'number' ? value.toFixed(2) : value}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )
                              } catch (e) {
                                return <div className="text-slate-300 text-xs whitespace-pre-wrap">{selectedPosition.exit_metadata}</div>
                              }
                            })()}
                          </div>
                        </div>
                      )}

                      {!selectedPosition.entry_metadata && !selectedPosition.exit_metadata && (
                        <div className="text-center text-slate-400 text-sm py-8">
                          No indicators available for this position
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800 text-center text-slate-400">
              No positions available
            </div>
          )}
        </>
      )}

      {/* Chart Overlay Modal */}
      {chartPosition && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-lg border border-slate-800 w-full max-w-6xl h-screen max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
              <div>
                <h2 className="text-2xl font-bold text-white">
                  {chartPosition.ticker} - Entry @ ${chartPosition.entry_price.toFixed(2)} | Exit @ ${chartPosition.exit_price.toFixed(2)}
                </h2>
                <p className="text-slate-400 text-sm mt-1">
                  {(() => {
                    try {
                      const entryMeta = typeof chartPosition.entry_metadata === 'string' ? JSON.parse(chartPosition.entry_metadata) : chartPosition.entry_metadata
                      const exitMeta = typeof chartPosition.exit_metadata === 'string' ? JSON.parse(chartPosition.exit_metadata) : chartPosition.exit_metadata
                      const entryDate = new Date(entryMeta?.timestamp || chartPosition.entry_date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                      const exitDate = new Date(exitMeta?.timestamp || chartPosition.exit_date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                      return `${entryDate} → ${exitDate}`
                    } catch {
                      return 'Position period'
                    }
                  })()}
                </p>
              </div>
              <button
                onClick={() => setChartPosition(null)}
                className="text-slate-400 hover:text-white transition text-2xl"
              >
                ✕
              </button>
            </div>

            {/* Chart Container */}
            <div className="flex-1 overflow-hidden">
              {(() => {
                try {
                  const entryMeta = typeof chartPosition.entry_metadata === 'string' ? JSON.parse(chartPosition.entry_metadata) : chartPosition.entry_metadata
                  const exitMeta = typeof chartPosition.exit_metadata === 'string' ? JSON.parse(chartPosition.exit_metadata) : chartPosition.exit_metadata
                  const entryDate = entryMeta?.timestamp || chartPosition.entry_date
                  const exitDate = exitMeta?.timestamp || chartPosition.exit_date
                  return <TradingChart timeframe="1M" title={`${chartPosition.ticker} - Position Analysis`} ticker={chartPosition.ticker} entryDate={entryDate} exitDate={exitDate} />
                } catch {
                  return <TradingChart timeframe="1M" title={`${chartPosition.ticker} - Position Analysis`} ticker={chartPosition.ticker} entryDate={chartPosition.entry_date} exitDate={chartPosition.exit_date} />
                }
              })()}
            </div>

            {/* Position Details */}
            <div className="px-6 py-4 border-t border-slate-800 bg-slate-800/30 grid grid-cols-6 gap-4 text-sm">
              <div>
                <p className="text-slate-400 text-xs mb-1">Quantity</p>
                <p className="text-white font-medium">{chartPosition.quantity}</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs mb-1">Entry Price</p>
                <p className="text-white font-medium">${chartPosition.entry_price.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs mb-1">Exit Price</p>
                <p className="text-white font-medium">${chartPosition.exit_price.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs mb-1">P&L</p>
                <p className={`font-medium ${chartPosition.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>${chartPosition.pnl.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs mb-1">Return</p>
                <p className={`font-medium ${chartPosition.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>{chartPosition.return_pct.toFixed(2)}%</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs mb-1">Close Reason</p>
                <p className="text-white font-medium text-xs">{chartPosition.close_reason}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Watchlist Tab */}
      {activeTab === 'watchlist' && (
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-white">Strategy Watchlist</h2>
              <p className="text-slate-400 text-sm mt-1">Stocks ranked by strategy relevance</p>
            </div>
            <button
              onClick={regenerateWatchlist}
              disabled={watchlistLoading}
              className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {watchlistLoading ? 'Regenerating...' : 'Regenerate'}
            </button>
          </div>

          {watchlistError && (
            <div className="bg-slate-900 rounded-lg border border-red-800/30 p-6">
              <div className="flex items-start gap-4">
                <div className="text-red-500 text-2xl">⚠️</div>
                <div>
                  <h3 className="text-red-400 font-medium mb-2">Unable to load watchlist</h3>
                  <p className="text-slate-400 text-sm">{watchlistError}</p>
                </div>
              </div>
            </div>
          )}

          {watchlistLoading && !watchlist.length && (
            <div className="flex items-center justify-center h-64">
              <div className="text-slate-400">Loading watchlist...</div>
            </div>
          )}

          {!watchlistLoading && watchlist.length === 0 && !watchlistError && (
            <div className="space-y-6">
              <div className="bg-slate-900 rounded-lg border border-slate-800 p-12 text-center text-slate-400">
                <p>No watchlist data available. The watchlist is generated during backtest execution.</p>
              </div>
            </div>
          )}

          {watchlist.length > 0 && (
            <div className="space-y-6">
              {/* View Toggle */}
              <div className="flex items-center gap-4 flex-wrap">
                <div className="flex items-center gap-2 bg-slate-800/30 border border-slate-700 rounded-lg p-1 w-fit">
                  <button
                    onClick={() => {
                      setWatchlistViewMode('table')
                      setWatchlistCurrentPage(1)
                    }}
                    className={`px-4 py-2 rounded transition font-medium text-sm ${
                      watchlistViewMode === 'table'
                        ? 'bg-purple-600 text-white'
                        : 'text-slate-400 hover:text-slate-300'
                    }`}
                  >
                    📊 Table
                  </button>
                  <button
                    onClick={() => {
                      setWatchlistViewMode('charts')
                      setWatchlistCurrentPage(1)
                    }}
                    className={`px-4 py-2 rounded transition font-medium text-sm ${
                      watchlistViewMode === 'charts'
                        ? 'bg-purple-600 text-white'
                        : 'text-slate-400 hover:text-slate-300'
                    }`}
                  >
                    📈 Charts
                  </button>
                </div>
              </div>

              {/* Filters */}
              <div className="flex items-center gap-4 flex-wrap">
                <div className="flex-1 min-w-64 relative">
                  <input
                    type="text"
                    placeholder="Search tickers"
                    value={watchlistSearch}
                    onChange={(e) => {
                      setWatchlistSearch(e.target.value)
                      setWatchlistCurrentPage(1)
                    }}
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg focus:outline-none focus:border-purple-600"
                  />
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500">🔍</span>
                </div>

                <select
                  value={watchlistSortBy}
                  onChange={(e) => {
                    setWatchlistSortBy(e.target.value)
                    setWatchlistCurrentPage(1)
                  }}
                  className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:border-slate-600 transition"
                >
                  <option>Score</option>
                  <option>Entry Score</option>
                  <option>RSI 14</option>
                  <option>RR Ratio</option>
                </select>
              </div>

              {/* Table View */}
              {watchlistViewMode === 'table' && (
                <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-800/50 border-b border-slate-800">
                        <tr>
                          <th className="px-6 py-4 text-left text-slate-400 font-medium">Ticker</th>
                          <th className="px-6 py-4 text-left text-slate-400 font-medium">Score</th>
                          <th className="px-6 py-4 text-left text-slate-400 font-medium">Signals</th>
                          <th className="px-6 py-4 text-left text-slate-400 font-medium">Entry Score</th>
                          <th className="px-6 py-4 text-left text-slate-400 font-medium">RR Ratio</th>
                          <th className="px-6 py-4 text-left text-slate-400 font-medium">RSI 14</th>
                          <th className="px-6 py-4 text-left text-slate-400 font-medium">ATR 14</th>
                          <th className="px-6 py-4 text-left text-slate-400 font-medium">Indicators</th>
                        </tr>
                      </thead>
                      <tbody>
                        {watchlist
                          .filter((item: any) => item.ticker.toLowerCase().includes(watchlistSearch.toLowerCase()))
                          .sort((a: any, b: any) => {
                            switch (watchlistSortBy) {
                              case 'Entry Score':
                                return (b.entry_score || 0) - (a.entry_score || 0)
                              case 'RSI 14':
                                return (b.rsi_14 || 0) - (a.rsi_14 || 0)
                              case 'RR Ratio':
                                return (b.rr_ratio || 0) - (a.rr_ratio || 0)
                              default:
                                return (b.signal_score || 0) - (a.signal_score || 0)
                            }
                          })
                          .map((item: any) => (
                            <tr key={item.ticker} className="border-t border-slate-800 hover:bg-slate-800/30 transition">
                              <td className="px-6 py-4 text-white font-medium">{item.ticker}</td>
                              <td className="px-6 py-4">
                                <div className="flex items-center gap-2">
                                  <div className="w-16 bg-slate-700 rounded-full h-2">
                                    <div
                                      className="bg-gradient-to-r from-purple-600 to-purple-500 h-2 rounded-full"
                                      style={{ width: `${Math.min(100, (item.signal_score || 0) * 100)}%` }}
                                    ></div>
                                  </div>
                                  <span className="text-white font-medium text-sm">{(item.signal_score || 0).toFixed(2)}</span>
                                </div>
                              </td>
                              <td className="px-6 py-4 text-slate-300 text-xs max-w-xs">{item.signals || '—'}</td>
                              <td className="px-6 py-4">
                                <span className="px-3 py-1 rounded text-xs font-medium bg-purple-900/30 text-purple-400">
                                  {item.entry_score || '—'}
                                </span>
                              </td>
                              <td className="px-6 py-4 text-white font-medium">{(parseFloat(item.rr_ratio) || 0).toFixed(2)}</td>
                              <td className="px-6 py-4 text-white font-medium">{(parseFloat(item.rsi_14) || 0).toFixed(2)}</td>
                              <td className="px-6 py-4 text-white font-medium">{(parseFloat(item.atr_14) || 0).toFixed(2)}</td>
                              <td className="px-6 py-4 text-xs text-slate-400">
                                EMA: {(parseFloat(item.ema_20) || 0).toFixed(2)} / {(parseFloat(item.ema_50) || 0).toFixed(2)}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  <div className="px-6 py-4 border-t border-slate-800 bg-slate-900 flex items-center justify-between">
                    <p className="text-slate-400 text-sm">Showing {watchlist.length} ticker{watchlist.length !== 1 ? 's' : ''}</p>
                  </div>
                </div>
              )}

              {/* Charts View */}
              {watchlistViewMode === 'charts' && (
                <div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {watchlist
                      .filter((item: any) => item.ticker.toLowerCase().includes(watchlistSearch.toLowerCase()))
                      .sort((a: any, b: any) => {
                        switch (watchlistSortBy) {
                          case 'Entry Score':
                            return (b.entry_score || 0) - (a.entry_score || 0)
                          case 'RSI 14':
                            return (b.rsi_14 || 0) - (a.rsi_14 || 0)
                          case 'RR Ratio':
                            return (b.rr_ratio || 0) - (a.rr_ratio || 0)
                          default:
                            return (b.signal_score || 0) - (a.signal_score || 0)
                        }
                      })
                      .map((item: any) => (
                        <div key={item.ticker} className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden hover:border-purple-600/50 transition">
                          {/* Card Header */}
                          <div className="bg-slate-800/50 border-b border-slate-800 p-4">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <p className="text-white font-bold text-lg">{item.ticker}</p>
                                <p className="text-slate-400 text-xs mt-0.5">{item.signals || 'No signals'}</p>
                              </div>
                              <div className="text-right ml-2 flex gap-3 items-start">
                                {/* Score and Trend */}
                                <div className="flex flex-col items-end gap-1">
                                  <div>
                                    <p className="text-3xl font-bold text-purple-400">{(item.signal_score || 0).toFixed(2)}</p>
                                    <p className="text-slate-400 text-xs -mt-1">Score</p>
                                  </div>
                                  {watchlistHistorical[item.ticker] && watchlistHistorical[item.ticker].length > 0 && (() => {
                                    const data = watchlistHistorical[item.ticker]
                                    const firstPrice = data[0]?.close || 0
                                    const lastPrice = data[data.length - 1]?.close || 0
                                    const variation = firstPrice !== 0 ? ((lastPrice - firstPrice) / firstPrice) * 100 : 0
                                    const isPositive = variation >= 0
                                    return (
                                      <div className={`text-lg font-bold flex items-center gap-1 ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                                        <span>{isPositive ? '↗' : '↘'}</span>
                                        <span>{isPositive ? '+' : ''}{variation.toFixed(2)}%</span>
                                      </div>
                                    )
                                  })()}
                                </div>

                                {/* Entry and RR Badges */}
                                <div className="flex flex-col gap-2 justify-start">
                                  <span className="px-2 py-1 rounded text-xs font-medium bg-purple-900/30 text-purple-400 whitespace-nowrap">
                                    Entry: {item.entry_score || '—'}
                                  </span>
                                  <span className="px-2 py-1 rounded text-xs font-medium bg-slate-800/30 text-slate-400 whitespace-nowrap">
                                    RR: {(parseFloat(item.rr_ratio) || 0).toFixed(2)}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Chart */}
                          {watchlistHistorical[item.ticker] && watchlistHistorical[item.ticker].length > 0 ? (
                            <CardChart
                              data={watchlistHistorical[item.ticker]}
                              ticker={item.ticker}
                              showVariation={false}
                            />
                          ) : (
                            <div className="p-4 h-48 bg-slate-800/20 flex items-center justify-center">
                              <p className="text-slate-400 text-sm">Loading chart...</p>
                            </div>
                          )}

                          {/* Card Footer */}
                          <div className="border-t border-slate-800 p-4 space-y-2">
                            <div className="text-xs">
                              <p className="text-slate-500 mb-1">Signals:</p>
                              <p className="text-slate-300">{item.signals || 'No signals'}</p>
                            </div>
                            <div className="flex justify-between text-xs pt-2 border-t border-slate-700">
                              <div>
                                <p className="text-slate-500">RSI 14</p>
                                <p className="text-white font-medium">{(parseFloat(item.rsi_14) || 0).toFixed(2)}</p>
                              </div>
                              <div>
                                <p className="text-slate-500">ATR 14</p>
                                <p className="text-white font-medium">{(parseFloat(item.atr_14) || 0).toFixed(2)}</p>
                              </div>
                              <div>
                                <p className="text-slate-500">EMA 20</p>
                                <p className="text-white font-medium">{(parseFloat(item.ema_20) || 0).toFixed(2)}</p>
                              </div>
                            </div>

                            {/* Additional Indicators */}
                            <div className="border-t border-slate-700 pt-2">
                              <p className="text-slate-500 mb-2 text-xs">More Indicators</p>
                              <div className="space-y-1 text-xs">
                                <div className="flex justify-between">
                                  <span className="text-slate-400">EMA 50</span>
                                  <span className="text-white font-medium">{(parseFloat(item.ema_50) || 0).toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-slate-400">ADX 20</span>
                                  <span className="text-white font-medium">{(parseFloat(item.adx_20) || 0).toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-slate-400">RR Ratio</span>
                                  <span className="text-white font-medium">{(parseFloat(item.rr_ratio) || 0).toFixed(2)}</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

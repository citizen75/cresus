import { useState, useEffect } from 'react'
import { useSearchParams, Link, useNavigate } from 'react-router-dom'
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { api } from '@/services/api'
import { useBacktestRuns } from '@/hooks/usePortfolio'

const CHART_COLORS = ['#a78bfa', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#8b5cf6']

export default function BacktestComparator() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { data: all_runs_data } = useBacktestRuns()

  const [selectedRuns, setSelectedRuns] = useState<string[]>([])
  const [compareData, setCompareData] = useState<Record<string, any>[]>([])
  const [loading, setLoading] = useState(false)

  const allRuns = all_runs_data?.backtests || []

  // Load initial selection from URL
  useEffect(() => {
    const items = searchParams.get('items')
    if (items) {
      const keys = items.split(',').filter(k => k.trim())
      setSelectedRuns(keys)
    }
  }, [searchParams])

  // Load comparison data when selection changes
  useEffect(() => {
    if (selectedRuns.length === 0) {
      setCompareData([])
      return
    }

    const loadData = async () => {
      setLoading(true)
      try {
        const result = await api.compareBacktests(selectedRuns)
        if (result.status === 'success') {
          setCompareData(result.data)
        }
      } catch (err) {
        console.error('Failed to load comparison data:', err)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [selectedRuns])

  const handleToggleRun = (key: string) => {
    const newSelected = selectedRuns.includes(key)
      ? selectedRuns.filter(k => k !== key)
      : [...selectedRuns, key].slice(-7) // Max 7 for readability

    setSelectedRuns(newSelected)

    // Update URL
    if (newSelected.length > 0) {
      navigate(`?items=${newSelected.join(',')}`)
    } else {
      navigate('')
    }
  }

  // Merge equity curves for overlay chart
  const mergedEquityCurves = selectedRuns.length > 0
    ? compareData.reduce((acc: any, run: any, idx: number) => {
        if (!run.equity_curve) return acc

        run.equity_curve.forEach((point: any) => {
          const existing = acc.find((p: any) => p.date === point.date)
          if (existing) {
            existing[`run_${idx}`] = point.value
          } else {
            const newPoint: any = { date: point.date }
            newPoint[`run_${idx}`] = point.value
            acc.push(newPoint)
          }
        })

        return acc
      }, [])
    : []

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">Compare Backtests</h1>
          <p className="text-slate-400">Overlay and compare multiple backtest runs</p>
        </div>
        <Link
          to="/backtests"
          className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-semibold transition"
        >
          Back to Runs
        </Link>
      </div>

      {/* Selected Runs Chips */}
      {selectedRuns.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selectedRuns.map((key, idx) => {
            const [strategy, id] = key.split(':')
            return (
              <div
                key={key}
                className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 rounded-full border border-slate-700"
                style={{ borderColor: CHART_COLORS[idx % CHART_COLORS.length] }}
              >
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: CHART_COLORS[idx % CHART_COLORS.length] }} />
                <span className="text-white text-sm font-semibold">{strategy}</span>
                <span className="text-slate-400 text-xs">{id.substring(0, 8)}</span>
                <button
                  onClick={() => handleToggleRun(key)}
                  className="ml-2 text-slate-400 hover:text-red-400 transition"
                >
                  ×
                </button>
              </div>
            )
          })}
        </div>
      )}

      <div className="grid grid-cols-4 gap-6">
        {/* Sidebar - Available Runs */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800 h-fit">
          <h3 className="text-lg font-bold text-white mb-4">Available Runs</h3>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {allRuns.slice(0, 20).map((run: any) => {
              const key = `${run.strategy_name}:${run.backtest_id}`
              const isSelected = selectedRuns.includes(key)

              return (
                <button
                  key={key}
                  onClick={() => handleToggleRun(key)}
                  className={`w-full text-left px-3 py-2 rounded transition text-sm ${
                    isSelected
                      ? 'bg-purple-600 text-white'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  <div className="font-semibold">{run.strategy_name}</div>
                  <div className="text-xs text-slate-500">{run.backtest_id.substring(0, 8)}</div>
                  <div className="text-xs mt-1">
                    {run.total_return_pct > 0 ? '+' : ''}{run.total_return_pct.toFixed(1)}%
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* Main Content */}
        <div className="col-span-3 space-y-8">
          {/* Equity Curve Chart */}
          <div className="bg-slate-900 rounded-lg p-8 border border-slate-800">
            <h3 className="text-xl font-bold text-white mb-6">Equity Curve Comparison</h3>
            {selectedRuns.length === 0 ? (
              <div className="h-80 flex items-center justify-center">
                <p className="text-slate-400">Select runs to compare</p>
              </div>
            ) : loading ? (
              <div className="h-80 flex items-center justify-center">
                <p className="text-slate-400">Loading...</p>
              </div>
            ) : (
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={mergedEquityCurves} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="date" stroke="#94a3b8" style={{ fontSize: '12px' }} />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }} />
                    <Legend />
                    {selectedRuns.map((_, idx) => (
                      <Line
                        key={`run_${idx}`}
                        type="monotone"
                        dataKey={`run_${idx}`}
                        stroke={CHART_COLORS[idx % CHART_COLORS.length]}
                        strokeWidth={2}
                        dot={false}
                        name={`Run ${idx + 1}`}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Metrics Comparison Table */}
          {selectedRuns.length > 0 && compareData.length > 0 && (
            <div className="bg-slate-900 rounded-lg p-8 border border-slate-800 overflow-x-auto">
              <h3 className="text-xl font-bold text-white mb-6">Performance Metrics</h3>
              <table className="w-full text-sm">
                <thead className="border-b border-slate-700">
                  <tr className="text-slate-400">
                    <th className="text-left py-3 px-3">Metric</th>
                    {compareData.map((run, idx) => (
                      <th key={idx} className="text-right py-3 px-3">
                        <div className="font-semibold">{run.strategy_name}</div>
                        <div className="text-xs text-slate-500">{run.backtest_id.substring(0, 8)}</div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[
                    { key: 'total_return_pct', label: 'Total Return' },
                    { key: 'sharpe_ratio', label: 'Sharpe Ratio' },
                    { key: 'sortino_ratio', label: 'Sortino Ratio' },
                    { key: 'calmar_ratio', label: 'Calmar Ratio' },
                    { key: 'max_drawdown_pct', label: 'Max Drawdown' },
                    { key: 'win_rate_pct', label: 'Win Rate' },
                    { key: 'profit_factor', label: 'Profit Factor' },
                    { key: 'total_trades', label: 'Total Trades' },
                    { key: 'expectancy_pct', label: 'Expectancy' },
                  ].map(metric => (
                    <tr key={metric.key} className="border-b border-slate-800 hover:bg-slate-800/30">
                      <td className="py-3 px-3 text-slate-400 font-semibold">{metric.label}</td>
                      {compareData.map((run: any, idx: number) => {
                        const value = run.portfolio_metrics?.[metric.key] || 0
                        const isReturn = metric.key.includes('pct')
                        const formatted = typeof value === 'number'
                          ? isReturn ? `${value.toFixed(2)}%` : `${value.toFixed(2)}`
                          : value

                        const isPositive = value > 0 && metric.key !== 'max_drawdown_pct'
                        const colorClass = isPositive
                          ? 'text-green-400'
                          : metric.key === 'max_drawdown_pct' ? 'text-red-400' : 'text-white'

                        return (
                          <td key={idx} className={`py-3 px-3 text-right font-semibold ${colorClass}`}>
                            {formatted}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

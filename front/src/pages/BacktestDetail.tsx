import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { LineChart, Line, AreaChart, Area, BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useBacktestRun } from '@/hooks/usePortfolio'

export default function BacktestDetail() {
  const { strategy, runId } = useParams<{ strategy: string; runId: string }>()
  const navigate = useNavigate()
  const { data: response, isLoading } = useBacktestRun(strategy || '', runId || '')
  const [activeTab, setActiveTab] = useState('performance')

  if (isLoading) {
    return <div className="text-slate-400">Loading backtest details...</div>
  }

  const backtest = response?.data
  if (!backtest) {
    return <div className="text-red-400">Backtest not found</div>
  }

  const metrics = backtest.portfolio_metrics || {}
  const equity = backtest.equity_curve || []
  const trades = backtest.trades || []
  const positions = backtest.positions || []

  // Build drawdown chart data
  const drawdownData = equity.map((point: any, idx: number) => {
    if (idx === 0) return { ...point, drawdown: 0 }
    const maxBefore = Math.max(...equity.slice(0, idx + 1).map((p: any) => p.value))
    const dd = ((point.value - maxBefore) / maxBefore) * 100
    return { ...point, drawdown: dd }
  })

  // Build monthly returns data
  const monthlyReturns = equity.reduce((acc: any, point: any) => {
    const date = new Date(point.date)
    const month = date.toLocaleString('en-US', { month: 'short', year: 'numeric' })
    if (!acc[month]) {
      acc[month] = { month, value: 0, returns: 0 }
    }
    return acc
  }, {})

  const TABS = [
    { id: 'performance', label: 'Performance' },
    { id: 'trades', label: 'Trades' },
    { id: 'overview', label: 'Overview' },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link to="/backtests" className="text-purple-400 hover:text-purple-300 text-sm mb-2 inline-block">
            ← Back to Runs
          </Link>
          <h1 className="text-4xl font-bold text-white mb-1">{runId}</h1>
          <p className="text-slate-400">{strategy} • {new Date(backtest.created_at).toLocaleDateString()}</p>
        </div>
        <button
          onClick={() => navigate(`/backtests/compare?items=${strategy}:${runId}`)}
          className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-semibold transition"
        >
          Compare
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-slate-800">
        <div className="flex gap-8">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-1 py-4 font-medium text-sm transition border-b-2 whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-purple-600 text-white'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Performance Tab */}
      {activeTab === 'performance' && (
        <div className="space-y-8">
          {/* Key Metrics Cards */}
          <div className="grid grid-cols-3 gap-6">
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <div className="text-slate-400 text-sm mb-2">Total Return</div>
              <div className={`text-3xl font-bold ${
                (metrics.total_return_pct || 0) >= 0 ? 'text-green-400' : 'text-red-400'
              }`}>
                {(metrics.total_return_pct || 0).toFixed(2)}%
              </div>
            </div>
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <div className="text-slate-400 text-sm mb-2">Sharpe Ratio</div>
              <div className="text-3xl font-bold text-white">{(metrics.sharpe_ratio || 0).toFixed(3)}</div>
            </div>
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <div className="text-slate-400 text-sm mb-2">Max Drawdown</div>
              <div className="text-3xl font-bold text-red-400">{(metrics.max_drawdown_pct || 0).toFixed(2)}%</div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-6">
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <div className="text-slate-400 text-sm mb-2">Sortino Ratio</div>
              <div className="text-3xl font-bold text-white">{(metrics.sortino_ratio || 0).toFixed(3)}</div>
            </div>
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <div className="text-slate-400 text-sm mb-2">Calmar Ratio</div>
              <div className="text-3xl font-bold text-white">{(metrics.calmar_ratio || 0).toFixed(3)}</div>
            </div>
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <div className="text-slate-400 text-sm mb-2">Profit Factor</div>
              <div className="text-3xl font-bold text-white">{(metrics.profit_factor || 0).toFixed(2)}</div>
            </div>
          </div>

          {/* Equity Curve */}
          <div className="bg-slate-900 rounded-lg p-8 border border-slate-800">
            <h3 className="text-xl font-bold text-white mb-6">Equity Curve</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={equity} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="date" stroke="#94a3b8" style={{ fontSize: '12px' }} />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }} />
                  <Line type="monotone" dataKey="value" stroke="#a78bfa" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Drawdown Chart */}
          <div className="bg-slate-900 rounded-lg p-8 border border-slate-800">
            <h3 className="text-xl font-bold text-white mb-6">Drawdown</h3>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={drawdownData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="date" stroke="#94a3b8" style={{ fontSize: '12px' }} />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }} />
                  <Area type="monotone" dataKey="drawdown" fill="#ef4444" stroke="#dc2626" fillOpacity={0.3} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Trade Statistics */}
          <div className="grid grid-cols-2 gap-6">
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <h3 className="text-lg font-bold text-white mb-4">Trade Statistics</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-slate-400">Total Trades</span>
                  <span className="text-white font-semibold">{metrics.total_trades || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Win Rate</span>
                  <span className="text-green-400 font-semibold">{(metrics.win_rate_pct || 0).toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Avg Winning Trade</span>
                  <span className="text-green-400 font-semibold">{(metrics.avg_winning_trade_pct || 0).toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Avg Losing Trade</span>
                  <span className="text-red-400 font-semibold">{(metrics.avg_losing_trade_pct || 0).toFixed(2)}%</span>
                </div>
              </div>
            </div>

            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <h3 className="text-lg font-bold text-white mb-4">Risk Metrics</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-slate-400">Max Drawdown Duration</span>
                  <span className="text-white font-semibold">{metrics.max_drawdown_duration_days || 0} days</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Expectancy</span>
                  <span className="text-white font-semibold">{(metrics.expectancy_pct || 0).toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Best Trade</span>
                  <span className="text-green-400 font-semibold">{(metrics.best_trade_pct || 0).toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Worst Trade</span>
                  <span className="text-red-400 font-semibold">{(metrics.worst_trade_pct || 0).toFixed(2)}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Trades Tab */}
      {activeTab === 'trades' && (
        <div className="bg-slate-900 rounded-lg p-8 border border-slate-800 overflow-x-auto">
          <h3 className="text-xl font-bold text-white mb-6">Trade History</h3>
          {trades.length === 0 ? (
            <div className="text-center py-8 text-slate-500">No trades recorded</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-slate-700">
                <tr className="text-slate-400">
                  <th className="text-left py-3 px-3">Date</th>
                  <th className="text-left py-3 px-3">Ticker</th>
                  <th className="text-right py-3 px-3">Operation</th>
                  <th className="text-right py-3 px-3">Quantity</th>
                  <th className="text-right py-3 px-3">Price</th>
                  <th className="text-right py-3 px-3">Amount</th>
                  <th className="text-left py-3 px-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {trades.slice(0, 50).map((trade: any, idx: number) => (
                  <tr key={idx} className="border-b border-slate-800 hover:bg-slate-800/30">
                    <td className="py-3 px-3 text-slate-400">{new Date(trade.created_at).toLocaleDateString()}</td>
                    <td className="py-3 px-3 text-white font-semibold">{trade.ticker}</td>
                    <td className={`py-3 px-3 text-right font-semibold ${
                      trade.operation === 'BUY' ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {trade.operation}
                    </td>
                    <td className="py-3 px-3 text-right text-white">{trade.quantity}</td>
                    <td className="py-3 px-3 text-right text-white">${(trade.price || 0).toFixed(2)}</td>
                    <td className="py-3 px-3 text-right text-white">${(trade.amount || 0).toFixed(2)}</td>
                    <td className={`py-3 px-3 text-sm ${
                      trade.status === 'completed' ? 'text-green-400' : 'text-amber-400'
                    }`}>
                      {trade.status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-2 gap-6">
          <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
            <h3 className="text-lg font-bold text-white mb-4">Backtest Info</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Strategy</span>
                <span className="text-white">{strategy}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Run ID</span>
                <span className="text-white font-mono">{runId}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Created</span>
                <span className="text-white">{new Date(backtest.created_at).toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Period</span>
                <span className="text-white">
                  {backtest.start_date} to {backtest.end_date}
                </span>
              </div>
            </div>
          </div>

          <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
            <h3 className="text-lg font-bold text-white mb-4">Current Positions</h3>
            {positions.length === 0 ? (
              <p className="text-slate-500 text-sm">No open positions</p>
            ) : (
              <div className="space-y-2 text-sm">
                {positions.map((pos: any, idx: number) => (
                  <div key={idx} className="flex justify-between">
                    <span className="text-slate-400">{pos.ticker}</span>
                    <span className="text-white">{pos.quantity} @ ${(pos.current_price || 0).toFixed(2)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

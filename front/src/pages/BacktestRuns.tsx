import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useBacktestRuns } from '@/hooks/usePortfolio'
import { api } from '@/services/api'

export default function BacktestRuns() {
  const navigate = useNavigate()
  const { data: backtest_data, isLoading, refetch } = useBacktestRuns()
  const [selectedRuns, setSelectedRuns] = useState<string[]>([])
  const [strategy_filter, setStrategy_filter] = useState<string>('')
  const [deleting, setDeleting] = useState<string>('')

  const backtests = backtest_data?.backtests || []
  const filteredBacktests = strategy_filter
    ? backtests.filter(b => b.strategy_name === strategy_filter)
    : backtests

  const strategies = [...new Set(backtests.map(b => b.strategy_name))]

  const handleDelete = async (strategy: string, id: string) => {
    setDeleting(`${strategy}:${id}`)
    try {
      await api.deleteBacktest(strategy, id)
      refetch()
    } catch (err) {
      console.error('Delete failed:', err)
    } finally {
      setDeleting('')
    }
  }

  const handleCompare = () => {
    if (selectedRuns.length > 0) {
      navigate(`/backtests/compare?items=${selectedRuns.join(',')}`)
    }
  }

  const toggleSelect = (key: string) => {
    setSelectedRuns(prev =>
      prev.includes(key)
        ? prev.filter(k => k !== key)
        : [...prev, key]
    )
  }

  if (isLoading) {
    return <div className="text-slate-400">Loading backtests...</div>
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">Backtest Runs</h1>
          <p className="text-slate-400">View and analyze historical backtest results</p>
        </div>
        <div className="flex gap-3">
          {selectedRuns.length > 0 && (
            <button
              onClick={handleCompare}
              className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-semibold transition"
            >
              Compare ({selectedRuns.length})
            </button>
          )}
          <Link
            to="/backtests/new"
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-violet-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-violet-700 transition"
          >
            + New Backtest
          </Link>
        </div>
      </div>

      {/* Filter */}
      <div className="flex gap-4 items-center">
        <label className="text-slate-400 text-sm font-medium">Strategy:</label>
        <select
          value={strategy_filter}
          onChange={e => setStrategy_filter(e.target.value)}
          className="bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 focus:border-purple-600 focus:outline-none"
        >
          <option value="">All Strategies</option>
          {strategies.map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {/* Backtests List */}
      <div className="space-y-3">
        {filteredBacktests.length === 0 ? (
          <div className="bg-slate-900 rounded-lg p-12 border border-slate-800 text-center">
            <p className="text-slate-500">No backtests found</p>
          </div>
        ) : (
          filteredBacktests.map(backtest => {
            const key = `${backtest.strategy_name}:${backtest.backtest_id}`
            const isSelected = selectedRuns.includes(key)
            const isDeleting = deleting === key

            return (
              <div
                key={key}
                className="bg-slate-900 rounded-lg p-6 border border-slate-800 hover:border-purple-600 transition cursor-pointer"
              >
                <div className="flex items-center gap-4">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleSelect(key)}
                    className="w-4 h-4 cursor-pointer"
                    onClick={e => e.stopPropagation()}
                  />

                  <Link
                    to={`/backtests/${backtest.strategy_name}/${backtest.backtest_id}`}
                    className="flex-1 hover:opacity-75 transition"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center text-white text-xs font-bold">
                            {backtest.strategy_name.substring(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <h3 className="text-white font-semibold">{backtest.backtest_id}</h3>
                            <p className="text-slate-400 text-sm">{backtest.strategy_name}</p>
                          </div>
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-green-400 font-semibold">{backtest.total_return_pct.toFixed(2)}%</div>
                        <div className="text-slate-400 text-sm">{new Date(backtest.created_at).toLocaleDateString()}</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-4 gap-4 mt-4">
                      <div className="bg-slate-800/50 rounded p-3">
                        <div className="text-slate-500 text-xs mb-1">Sharpe Ratio</div>
                        <div className="text-white font-semibold">{backtest.sharpe_ratio.toFixed(3)}</div>
                      </div>
                      <div className="bg-slate-800/50 rounded p-3">
                        <div className="text-slate-500 text-xs mb-1">Max Drawdown</div>
                        <div className="text-red-400 font-semibold">{backtest.max_drawdown_pct.toFixed(2)}%</div>
                      </div>
                      <div className="bg-slate-800/50 rounded p-3">
                        <div className="text-slate-500 text-xs mb-1">Win Rate</div>
                        <div className="text-white font-semibold">{backtest.win_rate_pct.toFixed(1)}%</div>
                      </div>
                      <div className="bg-slate-800/50 rounded p-3">
                        <div className="text-slate-500 text-xs mb-1">Trades</div>
                        <div className="text-white font-semibold">{backtest.total_trades}</div>
                      </div>
                    </div>
                  </Link>

                  <button
                    onClick={e => {
                      e.preventDefault()
                      handleDelete(backtest.strategy_name, backtest.backtest_id)
                    }}
                    disabled={isDeleting}
                    className="p-2 hover:bg-slate-800 rounded text-slate-400 hover:text-red-400 transition disabled:opacity-50"
                  >
                    {isDeleting ? '...' : '×'}
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

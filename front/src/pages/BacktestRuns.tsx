import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useBacktestRuns } from '@/hooks/usePortfolio'
import { api } from '@/services/api'

export default function BacktestRuns() {
  const navigate = useNavigate()
  const { data: backtest_data, isLoading, refetch } = useBacktestRuns()
  const [selectedRuns, setSelectedRuns] = useState<string[]>([])
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [strategyFilter, setStrategyFilter] = useState<string>('')
  const [deleteConfirm, setDeleteConfirm] = useState<string>('')
  const [deleting, setDeleting] = useState<string>('')

  const backtests = backtest_data?.backtests || [] as any[]
  const filteredBacktests = backtests.filter((b: any) => {
    const query = searchQuery.toLowerCase()
    const matchesSearch = (
      b.strategy_name.toLowerCase().includes(query) ||
      b.backtest_id.toLowerCase().includes(query)
    )
    const matchesStrategy = !strategyFilter || b.strategy_name === strategyFilter
    return matchesSearch && matchesStrategy
  })

  const strategies: string[] = [...new Set(backtests.map((b: any) => b.strategy_name) as string[])] as string[]

  const handleDelete = async (strategy: string, id: string) => {
    setDeleting(`${strategy}:${id}`)
    try {
      await api.deleteBacktest(strategy, id)
      refetch()
      setDeleteConfirm('')
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
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4">
          <div className="flex items-center justify-center w-12 h-12 rounded-full border-4 border-slate-700 border-t-purple-600 animate-spin mx-auto" />
          <p className="text-slate-400">Loading backtests...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="relative overflow-hidden rounded-xl border border-slate-700 bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800 p-6 shadow-lg">
        <div className="absolute inset-0 bg-gradient-to-r from-purple-600/10 to-violet-600/10 opacity-0 group-hover:opacity-100 transition-opacity" />
        <div className="relative flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-violet-400 bg-clip-text text-transparent">
              Backtest Runs
            </h1>
            <p className="text-slate-400 mt-1">
              {backtests.length} total • {selectedRuns.length} selected
            </p>
          </div>
          <div className="flex gap-2">
            {selectedRuns.length > 0 && (
              <button
                onClick={handleCompare}
                className="px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white rounded-lg text-sm font-semibold transition-all duration-200 shadow-lg hover:shadow-blue-500/50"
              >
                📊 Compare ({selectedRuns.length})
              </button>
            )}
            <Link
              to="/backtests/new"
              className="px-4 py-2 bg-gradient-to-r from-purple-600 to-violet-600 hover:from-purple-700 hover:to-violet-700 text-white rounded-lg text-sm font-semibold transition-all duration-200 shadow-lg hover:shadow-purple-500/50"
            >
              ✨ New Run
            </Link>
          </div>
        </div>
      </div>

      {/* Search & Filter Section */}
      <div className="flex gap-3 items-center">
        <div className="flex-1 relative">
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-lg">🔍</div>
          <input
            type="text"
            placeholder="Search by strategy or run ID..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full bg-slate-900/50 border border-slate-700 text-white rounded-lg pl-10 pr-4 py-2.5 text-sm placeholder-slate-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 focus:outline-none transition-all duration-200"
          />
        </div>

        <select
          value={strategyFilter}
          onChange={e => setStrategyFilter(e.target.value)}
          className="bg-slate-900/50 border border-slate-700 text-white rounded-lg px-4 py-2.5 text-sm focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 focus:outline-none transition-all duration-200 cursor-pointer"
        >
          <option value="">All Strategies</option>
          {strategies.map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <div className="px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-slate-400 text-sm font-medium whitespace-nowrap">
          {filteredBacktests.length}/{backtests.length}
        </div>
      </div>

      {/* Backtests Table */}
      <div className="rounded-xl border border-slate-700 overflow-hidden shadow-xl bg-gradient-to-b from-slate-900 to-slate-900/50">
        {filteredBacktests.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-4xl mb-3">📭</div>
            <p className="text-slate-400">No backtests found</p>
            {searchQuery && <p className="text-slate-500 text-sm mt-1">Try adjusting your search</p>}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 border-b border-slate-700 bg-slate-800/50 backdrop-blur-sm">
                <tr className="text-slate-400 text-xs font-semibold uppercase tracking-wide">
                  <th className="w-6 px-4 py-3 text-left"></th>
                  <th className="px-4 py-3 text-left">Strategy</th>
                  <th className="px-4 py-3 text-left">Run ID</th>
                  <th className="px-4 py-3 text-right">Return</th>
                  <th className="px-4 py-3 text-right">Sharpe</th>
                  <th className="px-4 py-3 text-right">Drawdown</th>
                  <th className="px-4 py-3 text-right">Win Rate</th>
                  <th className="px-4 py-3 text-right">Trades</th>
                  <th className="px-4 py-3 text-right">Period</th>
                  <th className="px-4 py-3 text-right">Date</th>
                  <th className="w-12 px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {filteredBacktests.map((backtest: any) => {
                  const key = `${backtest.strategy_name}:${backtest.backtest_id}`
                  const isSelected = selectedRuns.includes(key)
                  const isDeleting = deleting === key
                  const showDeleteConfirm = deleteConfirm === key

                  return (
                    <tr
                      key={key}
                      className={`border-b border-slate-700 transition-all duration-150 cursor-pointer ${
                        isSelected
                          ? 'bg-purple-600/15'
                          : 'hover:bg-slate-800/30'
                      }`}
                      onClick={() => !showDeleteConfirm && navigate(`/backtests/${backtest.strategy_name}/${backtest.backtest_id}`)}
                    >
                      <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(key)}
                          className="w-4 h-4 cursor-pointer accent-purple-600 rounded"
                        />
                      </td>

                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-7 h-7 bg-gradient-to-br from-purple-600 to-violet-600 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-lg">
                            {backtest.strategy_name.substring(0, 1).toUpperCase()}
                          </div>
                          <span className="text-white font-semibold">{backtest.strategy_name}</span>
                        </div>
                      </td>

                      <td className="px-4 py-3">
                        <code className="text-slate-400 bg-slate-800/50 px-2 py-1 rounded text-xs font-mono">
                          {backtest.backtest_id.substring(0, 17)}...
                        </code>
                      </td>

                      <td className={`px-4 py-3 text-right font-bold text-sm ${
                        backtest.total_return_pct >= 0
                          ? 'text-green-400'
                          : 'text-red-400'
                      }`}>
                        {backtest.total_return_pct >= 0 ? '+' : ''}{backtest.total_return_pct.toFixed(1)}%
                      </td>

                      <td className="px-4 py-3 text-right">
                        <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
                          backtest.sharpe_ratio > 1
                            ? 'bg-green-600/20 text-green-300'
                            : backtest.sharpe_ratio > 0
                            ? 'bg-yellow-600/20 text-yellow-300'
                            : 'bg-red-600/20 text-red-300'
                        }`}>
                          {backtest.sharpe_ratio.toFixed(2)}
                        </span>
                      </td>

                      <td className="px-4 py-3 text-right">
                        <span className="text-red-400 font-semibold">
                          -{backtest.max_drawdown_pct.toFixed(1)}%
                        </span>
                      </td>

                      <td className="px-4 py-3 text-right">
                        <span className="inline-block px-2 py-1 rounded text-xs font-semibold bg-blue-600/20 text-blue-300">
                          {backtest.win_rate_pct.toFixed(0)}%
                        </span>
                      </td>

                      <td className="px-4 py-3 text-right text-white font-medium">
                        {backtest.total_trades}
                      </td>

                      <td className="px-4 py-3 text-right text-slate-400 text-xs">
                        {backtest.start_date && backtest.end_date ? (
                          <div className="flex flex-col gap-0.5">
                            <span>{new Date(backtest.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' })}</span>
                            <span className="text-slate-500">to</span>
                            <span>{new Date(backtest.end_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' })}</span>
                          </div>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>

                      <td className="px-4 py-3 text-right text-slate-400 text-xs">
                        <div className="flex flex-col gap-0.5">
                          <span>{new Date(backtest.created_at).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: '2-digit'
                          })}</span>
                          <span className="text-slate-500">{new Date(backtest.created_at).toLocaleTimeString('en-US', {
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                            hour12: false
                          })}</span>
                        </div>
                      </td>

                      <td className="px-4 py-3 text-right" onClick={e => e.stopPropagation()}>
                        {showDeleteConfirm ? (
                          <div className="flex gap-1.5 justify-end">
                            <button
                              onClick={() => handleDelete(backtest.strategy_name, backtest.backtest_id)}
                              disabled={isDeleting}
                              className="px-2.5 py-1 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded transition-all duration-150 disabled:opacity-50 shadow-lg"
                            >
                              {isDeleting ? '⏳' : '✓'}
                            </button>
                            <button
                              onClick={() => setDeleteConfirm('')}
                              className="px-2.5 py-1 bg-slate-700 hover:bg-slate-600 text-white text-xs font-semibold rounded transition-all duration-150"
                            >
                              ✕
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setDeleteConfirm(key)}
                            className="text-slate-500 hover:text-red-400 hover:bg-red-600/10 transition-all duration-150 rounded-lg p-1.5 text-lg leading-none"
                            title="Delete backtest"
                          >
                            🗑️
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

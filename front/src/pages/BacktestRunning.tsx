import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import { api } from '@/services/api'

export default function BacktestRunning() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const strategy = searchParams.get('strategy') || ''
  const startDate = searchParams.get('start') || ''
  const endDate = searchParams.get('end') || ''

  const [status, setStatus] = useState('initializing')
  const [backtest_id, setBacktestId] = useState('')
  const [progress, setProgress] = useState({
    current: 0,
    total: 0,
    percentage: 0,
  })
  const [error, setError] = useState('')
  const [logs, setLogs] = useState<string[]>([])
  const [metrics, setMetrics] = useState<any>(null)

  // Start the backtest
  useEffect(() => {
    const runBacktest = async () => {
      try {
        setStatus('running')
        setLogs(['Starting backtest...'])

        const result = await api.runBacktest({
          strategy,
          start_date: startDate,
          end_date: endDate,
        })

        if (result.backtest_id) {
          setBacktestId(result.backtest_id)
          setLogs(prev => [...prev, 'Backtest completed!'])
          setMetrics(result.output?.portfolio_metrics)

          // Wait a moment for the screen to update, then navigate
          setTimeout(() => {
            navigate(`/backtests/${strategy}/${result.backtest_id}`)
          }, 1500)
        } else {
          setStatus('error')
          setError('Failed to get backtest ID')
          setLogs(prev => [...prev, `Error: ${result.message || 'Unknown error'}`])
        }
      } catch (err: any) {
        setStatus('error')
        const errorMsg = err.response?.data?.detail || err.message || 'Failed to run backtest'
        setError(errorMsg)
        setLogs(prev => [...prev, `Error: ${errorMsg}`])
      }
    }

    if (strategy && startDate && endDate) {
      runBacktest()
    }
  }, [strategy, startDate, endDate, navigate])

  // Simulate progress (since we don't have real-time progress from backend)
  useEffect(() => {
    if (status === 'running') {
      const interval = setInterval(() => {
        setProgress(prev => {
          if (prev.percentage >= 95) return prev
          const newPercentage = Math.min(prev.percentage + Math.random() * 15, 95)
          return { ...prev, percentage: newPercentage }
        })
      }, 500)

      return () => clearInterval(interval)
    }
  }, [status])

  // When backtest completes, set progress to 100
  useEffect(() => {
    if (backtest_id) {
      setProgress({ current: 100, total: 100, percentage: 100 })
      setStatus('completed')
    }
  }, [backtest_id])

  const isSuccess = status === 'completed'
  const isFailed = status === 'error'

  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-950">
      <div className="w-full max-w-2xl mx-auto px-8">
        <div className="space-y-8">
          {/* Status Card */}
          <div className="bg-slate-900 rounded-lg p-12 border border-slate-800 space-y-6">
            {/* Status Icon */}
            <div className="flex justify-center">
              {status === 'initializing' || status === 'running' ? (
                <div className="flex items-center justify-center w-20 h-20 rounded-full border-4 border-slate-700 border-t-purple-600 animate-spin" />
              ) : isSuccess ? (
                <div className="flex items-center justify-center w-20 h-20 rounded-full bg-green-900/30 border-2 border-green-500">
                  <span className="text-4xl text-green-400">✓</span>
                </div>
              ) : (
                <div className="flex items-center justify-center w-20 h-20 rounded-full bg-red-900/30 border-2 border-red-500">
                  <span className="text-4xl text-red-400">✕</span>
                </div>
              )}
            </div>

            {/* Status Text */}
            <div className="text-center space-y-2">
              <h2 className="text-3xl font-bold text-white">
                {status === 'initializing' && 'Initializing...'}
                {status === 'running' && 'Running Backtest'}
                {isSuccess && 'Backtest Complete!'}
                {isFailed && 'Backtest Failed'}
              </h2>
              <p className="text-slate-400">
                {status === 'initializing' && 'Preparing backtest environment...'}
                {status === 'running' && `Strategy: ${strategy} • Period: ${startDate} to ${endDate}`}
                {isSuccess && 'Your backtest results are ready'}
                {isFailed && 'An error occurred during execution'}
              </p>
            </div>

            {/* Progress Bar */}
            {status === 'running' || status === 'initializing' ? (
              <div className="space-y-3">
                <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden border border-slate-700">
                  <div
                    className="h-full bg-gradient-to-r from-purple-600 to-violet-600 transition-all duration-300"
                    style={{ width: `${progress.percentage}%` }}
                  />
                </div>
                <div className="text-center text-slate-400 text-sm">
                  {Math.round(progress.percentage)}% complete
                </div>
              </div>
            ) : null}

            {/* Error Message */}
            {isFailed && error && (
              <div className="p-4 bg-red-900/30 border border-red-800 rounded text-red-400 text-sm">
                {error}
              </div>
            )}

            {/* Metrics Preview (on success) */}
            {isSuccess && metrics && (
              <div className="space-y-3">
                <div className="text-sm text-slate-400 font-semibold">Results Preview:</div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-800/50 rounded p-3">
                    <div className="text-slate-500 text-xs mb-1">Total Return</div>
                    <div className={`text-lg font-bold ${
                      (metrics.total_return_pct || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {(metrics.total_return_pct || 0).toFixed(2)}%
                    </div>
                  </div>
                  <div className="bg-slate-800/50 rounded p-3">
                    <div className="text-slate-500 text-xs mb-1">Sharpe Ratio</div>
                    <div className="text-lg font-bold text-white">
                      {(metrics.sharpe_ratio || 0).toFixed(3)}
                    </div>
                  </div>
                  <div className="bg-slate-800/50 rounded p-3">
                    <div className="text-slate-500 text-xs mb-1">Max Drawdown</div>
                    <div className="text-lg font-bold text-red-400">
                      {(metrics.max_drawdown_pct || 0).toFixed(2)}%
                    </div>
                  </div>
                  <div className="bg-slate-800/50 rounded p-3">
                    <div className="text-slate-500 text-xs mb-1">Win Rate</div>
                    <div className="text-lg font-bold text-white">
                      {(metrics.win_rate_pct || 0).toFixed(1)}%
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Logs */}
            <div className="space-y-2">
              <div className="text-sm text-slate-400 font-semibold">Activity Log:</div>
              <div className="bg-slate-950 rounded p-4 border border-slate-800 max-h-32 overflow-y-auto space-y-1">
                {logs.map((log, idx) => (
                  <div key={idx} className="text-xs text-slate-400 font-mono">
                    <span className="text-slate-600">→</span> {log}
                  </div>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4">
              <Link
                to="/backtests"
                className="flex-1 px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-semibold transition text-center"
              >
                Back to Runs
              </Link>
              {isSuccess && (
                <button
                  onClick={() => navigate(`/backtests/${strategy}/${backtest_id}`)}
                  className="flex-1 px-6 py-3 bg-gradient-to-r from-purple-600 to-violet-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-violet-700 transition"
                >
                  View Results
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

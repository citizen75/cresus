import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '@/services/api'

export default function BacktestBuilder() {
  const navigate = useNavigate()

  const [strategy, setStrategy] = useState('')
  const [strategies, setStrategies] = useState<string[]>([])
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // Set default date range (1 year back)
    const end = new Date()
    const start = new Date(end.getFullYear() - 1, end.getMonth(), end.getDate())

    setEndDate(end.toISOString().split('T')[0])
    setStartDate(start.toISOString().split('T')[0])
  }, [])

  useEffect(() => {
    // Load strategies list from portfolios if available
    // For now, use a hardcoded list from user's typical strategies
    // In a real app, you'd fetch from /strategies API
    setStrategies(['etf_pea_trend', 'etf_pea_momentum', 'cac_pullback'])
  }, [])

  const handleQuickDate = (years: number) => {
    const end = new Date()
    const start = new Date(end.getFullYear() - years, end.getMonth(), end.getDate())
    setStartDate(start.toISOString().split('T')[0])
    setEndDate(end.toISOString().split('T')[0])
  }

  const handleSubmit = async () => {
    if (!strategy || !startDate || !endDate) {
      return
    }

    setLoading(true)
    try {
      const response = await api.runBacktest({
        strategy,
        start_date: startDate,
        end_date: endDate,
      })

      if (response.backtest_id) {
        // Navigate directly to detail page
        navigate(`/backtests/${strategy}/${response.backtest_id}`)
      }
    } catch (err) {
      console.error('Failed to start backtest:', err)
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <Link to="/backtests" className="text-purple-400 hover:text-purple-300 text-sm mb-4 inline-block">
          ← Back to Runs
        </Link>
        <h1 className="text-4xl font-bold text-white mb-2">Create New Backtest</h1>
        <p className="text-slate-400">Configure and run a backtest on your trading strategy</p>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-8">
        {/* Form */}
        <div className="col-span-2 space-y-6">

          {/* Step 1: Strategy Selection */}
          <div className="bg-slate-900 rounded-lg p-8 border border-slate-800">
            <div className="flex items-center mb-6">
              <div className="w-10 h-10 rounded-full flex items-center justify-center font-bold bg-purple-600 text-white">
                1
              </div>
              <h2 className="ml-4 text-2xl font-bold text-white">Select Strategy</h2>
            </div>

            <div className="space-y-3">
              <label className="block text-slate-400 text-sm font-medium">Trading Strategy</label>
              <select
                value={strategy}
                onChange={e => setStrategy(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-3 focus:border-purple-600 focus:outline-none"
              >
                <option value="">Choose a strategy...</option>
                {strategies.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Step 2: Date Range */}
          <div className="bg-slate-900 rounded-lg p-8 border border-slate-800">
            <div className="flex items-center mb-6">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                strategy ? 'bg-purple-600 text-white' : 'bg-slate-700 text-slate-400'
              }`}>
                2
              </div>
              <h2 className="ml-4 text-2xl font-bold text-white">Select Period</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-slate-400 text-sm font-medium mb-2">Quick Select</label>
                <div className="flex gap-2">
                  {[1, 2, 5].map(years => (
                    <button
                      key={years}
                      onClick={() => handleQuickDate(years)}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition"
                    >
                      {years}Y
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 text-sm font-medium mb-2">Start Date</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={e => setStartDate(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 focus:border-purple-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 text-sm font-medium mb-2">End Date</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={e => setEndDate(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 focus:border-purple-600 focus:outline-none"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Step 3: Review & Run */}
          <div className="bg-slate-900 rounded-lg p-8 border border-slate-800">
            <div className="flex items-center mb-6">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                strategy && startDate && endDate ? 'bg-purple-600 text-white' : 'bg-slate-700 text-slate-400'
              }`}>
                3
              </div>
              <h2 className="ml-4 text-2xl font-bold text-white">Review & Run</h2>
            </div>

            <p className="text-slate-400 mb-6">
              Click the button below to start the backtest. This may take a few moments depending on the date range and complexity.
            </p>

            <button
              onClick={handleSubmit}
              disabled={!strategy || !startDate || !endDate || loading}
              className="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-violet-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-violet-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Starting...' : 'Run Backtest'}
            </button>
          </div>
        </div>

        {/* Summary Sidebar */}
        <div className="col-span-1">
          <div className="sticky top-8 bg-slate-900 rounded-lg p-6 border border-slate-800 space-y-6">
            <h3 className="text-xl font-bold text-white">Summary</h3>

            <div className="space-y-4">
              <div>
                <div className="text-slate-400 text-sm mb-2">Strategy</div>
                <div className="text-white font-semibold">{strategy || '—'}</div>
              </div>

              <div>
                <div className="text-slate-400 text-sm mb-2">Period</div>
                <div className="text-white font-semibold">
                  {startDate && endDate
                    ? `${startDate} to ${endDate}`
                    : '—'
                  }
                </div>
                {startDate && endDate && (
                  <div className="text-slate-400 text-xs mt-1">
                    {Math.round((new Date(endDate).getTime() - new Date(startDate).getTime()) / (1000 * 60 * 60 * 24))} days
                  </div>
                )}
              </div>

              <div className="border-t border-slate-700 pt-4">
                <div className="text-slate-400 text-sm mb-2">Status</div>
                <div className="text-amber-400 text-sm font-semibold">
                  {strategy && startDate && endDate ? '✓ Ready to run' : '○ Incomplete'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'

interface StrategyBuilderProps {
  name: string
}

interface Strategy {
  name: string
  universe: string
  description: string
  engine: string
  indicators: string[]
  buy_conditions: string
  sell_conditions: string
  watchlist?: {
    enabled: boolean
    parameters: Record<string, any>
  }
  signals?: {
    enabled: boolean
    weights: Record<string, number>
    parameters: Record<string, any>
  }
  entry?: {
    enabled: boolean
    parameters: Record<string, any>
  }
  exit?: {
    enabled: boolean
    parameters: Record<string, any>
  }
  backtest?: {
    initial_capital: number
  }
}

export default function StrategyBuilder({ name }: StrategyBuilderProps) {
  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingWatchlist, setEditingWatchlist] = useState(false)

  useEffect(() => {
    const fetchStrategy = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/v1/strategies/${name}`)
        if (!response.ok) {
          throw new Error(`Failed to fetch strategy: ${response.statusText}`)
        }
        const data = await response.json()
        setStrategy(data.strategy)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchStrategy()
  }, [name])

  if (loading) {
    return <div className="text-slate-400 py-12 text-center">Loading strategy...</div>
  }

  if (error) {
    return <div className="text-red-400 py-12 text-center">Error: {error}</div>
  }

  if (!strategy) {
    return <div className="text-slate-400 py-12 text-center">Strategy not found</div>
  }

  return (
    <div className="space-y-6">
      {/* Header with Save Button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Strategy definition</h2>
          <p className="text-slate-400 text-sm mt-1">{strategy.description}</p>
        </div>
        <button className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition">
          Save strategy
        </button>
      </div>

      {/* Strategy Status */}
      <div className="flex items-center gap-2 text-sm">
        <span className="w-2 h-2 bg-green-400 rounded-full"></span>
        <span className="text-green-400">Strategy active</span>
      </div>

      {/* Strategy Info Cards */}
      <div className="grid grid-cols-5 gap-6">
        {/* Universe */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <h3 className="text-white font-bold mb-4">Universe</h3>
          <div className="space-y-3">
            <div className="bg-slate-800/50 rounded p-3">
              <p className="text-slate-400 text-xs uppercase mb-1">Universe</p>
              <p className="text-white font-medium text-sm capitalize">{strategy.universe.replace(/_/g, ' ')}</p>
            </div>
            <div className="bg-slate-800/50 rounded p-3">
              <p className="text-slate-400 text-xs uppercase mb-1">Engine</p>
              <p className="text-white font-medium text-sm">{strategy.engine}</p>
            </div>
          </div>
          <button className="w-full mt-4 px-4 py-2 text-purple-400 hover:text-purple-300 text-sm font-medium transition">
            Edit universe
          </button>
        </div>

        {/* Entry Conditions */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <h3 className="text-white font-bold mb-4">Entry</h3>
          {strategy.entry?.enabled ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 p-2 bg-green-900/20 rounded border border-green-800/50">
                <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                <span className="text-green-400 text-xs font-medium">Enabled</span>
              </div>
              {strategy.entry.parameters?.position_size && (
                <div className="text-slate-300 text-xs bg-slate-800/30 p-2 rounded font-mono break-all">
                  {strategy.entry.parameters.position_size.formula}
                </div>
              )}
            </div>
          ) : (
            <div className="text-slate-400 text-sm">Not configured</div>
          )}
          <button className="w-full mt-4 px-4 py-2 text-purple-400 hover:text-purple-300 text-sm font-medium transition">
            Edit entry
          </button>
        </div>

        {/* Exit Conditions */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <h3 className="text-white font-bold mb-4">Exit</h3>
          {strategy.exit?.enabled ? (
            <div className="space-y-2 text-xs">
              <div className="flex items-center gap-2 p-2 bg-red-900/20 rounded border border-red-800/50">
                <span className="w-2 h-2 bg-red-400 rounded-full"></span>
                <span className="text-red-400 font-medium">Stop Loss</span>
              </div>
              {strategy.exit.parameters?.stop_loss && (
                <div className="text-slate-300 bg-slate-800/30 p-2 rounded font-mono break-all">
                  {strategy.exit.parameters.stop_loss.formula}
                </div>
              )}
              {strategy.exit.parameters?.take_profit && (
                <div>
                  <span className="text-slate-400">Take Profit:</span>
                  <div className="text-slate-300 bg-slate-800/30 p-2 rounded font-mono break-all">
                    {strategy.exit.parameters.take_profit.formula}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-slate-400 text-sm">Not configured</div>
          )}
          <button className="w-full mt-4 px-4 py-2 text-purple-400 hover:text-purple-300 text-sm font-medium transition">
            Edit exit
          </button>
        </div>

        {/* Indicators */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <h3 className="text-white font-bold mb-4">Indicators</h3>
          <div className="space-y-2">
            {strategy.indicators?.map((indicator) => (
              <div key={indicator} className="flex items-center gap-2 p-2 bg-blue-900/20 rounded border border-blue-800/50">
                <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
                <span className="text-blue-400 text-xs font-medium">{indicator}</span>
              </div>
            ))}
          </div>
          <button className="w-full mt-4 px-4 py-2 text-purple-400 hover:text-purple-300 text-sm font-medium transition">
            Manage indicators
          </button>
        </div>

        {/* Watchlist Config */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-bold">Watchlist</h3>
            <button
              onClick={() => setEditingWatchlist(!editingWatchlist)}
              className="text-purple-400 hover:text-purple-300 text-sm font-medium"
            >
              {editingWatchlist ? 'Done' : 'Edit'}
            </button>
          </div>

          {editingWatchlist ? (
            // Edit Form
            <div className="space-y-3">
              <div>
                <label className="text-slate-400 text-xs uppercase block mb-1">Volume Min</label>
                <input
                  type="number"
                  defaultValue={strategy.watchlist?.parameters?.volume?.min_volume || 500000}
                  className="w-full bg-slate-800 border border-slate-700 text-white px-2 py-1 rounded text-xs"
                />
              </div>
              <div>
                <label className="text-slate-400 text-xs uppercase block mb-1">Ranking</label>
                <input
                  type="text"
                  defaultValue={strategy.watchlist?.parameters?.ranking?.metric || 'score'}
                  className="w-full bg-slate-800 border border-slate-700 text-white px-2 py-1 rounded text-xs"
                />
              </div>
              <div>
                <label className="text-slate-400 text-xs uppercase block mb-1">Trend</label>
                <textarea
                  defaultValue={strategy.watchlist?.parameters?.trend?.formula || ''}
                  className="w-full bg-slate-800 border border-slate-700 text-white px-2 py-1 rounded text-xs font-mono h-12"
                />
              </div>
              <div>
                <label className="text-slate-400 text-xs uppercase block mb-1">Volatility</label>
                <textarea
                  defaultValue={strategy.watchlist?.parameters?.volatility?.formula || ''}
                  className="w-full bg-slate-800 border border-slate-700 text-white px-2 py-1 rounded text-xs font-mono h-12"
                />
              </div>
            </div>
          ) : (
            // Display View
            <div className="space-y-2 text-xs">
              {strategy.watchlist?.parameters?.volume && (
                <div className="bg-slate-800/50 rounded p-2">
                  <p className="text-slate-400 uppercase mb-1">Volume Min</p>
                  <p className="text-white font-medium">{strategy.watchlist.parameters.volume.min_volume?.toLocaleString()}</p>
                </div>
              )}
              {strategy.watchlist?.parameters?.ranking && (
                <div className="bg-slate-800/50 rounded p-2">
                  <p className="text-slate-400 uppercase mb-1">Ranking</p>
                  <p className="text-white font-medium">{strategy.watchlist.parameters.ranking.metric}</p>
                </div>
              )}
              {strategy.watchlist?.parameters?.trend && (
                <div className="bg-slate-800/50 rounded p-2">
                  <p className="text-slate-400 uppercase mb-1 text-xs">Trend</p>
                  <p className="text-slate-300 text-xs font-mono break-all line-clamp-2">{strategy.watchlist.parameters.trend.formula}</p>
                </div>
              )}
              {strategy.watchlist?.parameters?.volatility && (
                <div className="bg-slate-800/50 rounded p-2">
                  <p className="text-slate-400 uppercase mb-1 text-xs">Volatility</p>
                  <p className="text-slate-300 text-xs font-mono break-all line-clamp-2">{strategy.watchlist.parameters.volatility.formula}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Signals Configuration */}
      {strategy.signals?.enabled && (
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <h3 className="text-white font-bold text-lg mb-6">Signal Weights</h3>
          <div className="grid grid-cols-4 gap-4">
            {Object.entries(strategy.signals.weights).map(([key, value]) => (
              <div key={key} className="bg-slate-800/50 rounded p-4">
                <p className="text-slate-400 text-xs uppercase mb-2 capitalize">{key.replace(/_/g, ' ')}</p>
                <p className="text-white font-bold text-2xl">{(value * 100).toFixed(0)}%</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

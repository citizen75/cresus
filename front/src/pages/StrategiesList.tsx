import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/services/api'

interface Strategy {
  name: string
  description: string
  source?: string
  file?: string
}

export default function StrategiesList() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadStrategies = async () => {
      try {
        const result = await api.listStrategies()
        setStrategies(result.strategies || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load strategies')
      } finally {
        setLoading(false)
      }
    }

    loadStrategies()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-slate-400">Loading strategies...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-red-400 py-12 text-center">{error}</div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Strategies</h1>
        <p className="text-slate-400">Manage and configure your trading strategies</p>
      </div>

      {/* Strategies Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {strategies.map((strategy) => (
          <Link
            key={strategy.name}
            to={`/strategies/${encodeURIComponent(strategy.name)}`}
            className="group bg-slate-900 rounded-lg border border-slate-800 p-6 hover:border-purple-600/50 hover:bg-slate-800/50 transition"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="w-10 h-10 bg-purple-900/30 rounded-lg flex items-center justify-center group-hover:bg-purple-900/50 transition">
                <span className="text-purple-400 text-lg">📊</span>
              </div>
              <span className="text-xs px-2 py-1 bg-slate-700/50 text-slate-300 rounded capitalize">
                {strategy.source || 'custom'}
              </span>
            </div>

            <h3 className="text-white font-bold text-lg mb-2 group-hover:text-purple-400 transition">
              {strategy.name}
            </h3>

            <p className="text-slate-400 text-sm mb-4 line-clamp-2">
              {strategy.description || 'No description available'}
            </p>

            <div className="flex items-center gap-2 text-purple-400 text-xs font-medium group-hover:gap-3 transition">
              <span>View Strategy</span>
              <span>→</span>
            </div>
          </Link>
        ))}
      </div>

      {strategies.length === 0 && (
        <div className="text-center py-12">
          <div className="text-slate-400">No strategies found</div>
        </div>
      )}
    </div>
  )
}

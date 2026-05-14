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
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

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

  useEffect(() => {
    loadStrategies()
  }, [])

  const handleDelete = async (name: string) => {
    setDeleting(true)
    try {
      await api.deleteStrategy(name)
      setStrategies(strategies.filter(s => s.name !== name))
      setDeleteConfirm(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete strategy')
    } finally {
      setDeleting(false)
    }
  }

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
          <div key={strategy.name} className="group bg-slate-900 rounded-lg border border-slate-800 overflow-hidden hover:border-purple-600/50 hover:bg-slate-800/50 transition">
            <Link
              to={`/strategies/${encodeURIComponent(strategy.name)}`}
              className="block p-6"
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

            <div className="flex items-center justify-between px-6 py-3 border-t border-slate-700 bg-slate-900/50">
              <button
                onClick={(e) => {
                  e.preventDefault()
                  setDeleteConfirm(strategy.name)
                }}
                className="flex items-center gap-2 px-3 py-2 text-red-400 hover:text-red-300 hover:bg-red-900/20 rounded text-sm transition"
                title="Delete strategy"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                <span>Delete</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-6 max-w-sm">
            <h3 className="text-lg font-bold text-white mb-2">Delete Strategy?</h3>
            <p className="text-slate-400 mb-6">
              Are you sure you want to delete <span className="font-semibold text-white">"{deleteConfirm}"</span>? This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                disabled={deleting}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                disabled={deleting}
                className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded transition disabled:opacity-50"
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {strategies.length === 0 && (
        <div className="text-center py-12">
          <div className="text-slate-400">No strategies found</div>
        </div>
      )}
    </div>
  )
}

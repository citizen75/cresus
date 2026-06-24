import { useState, useEffect } from 'react'
import { getApiBaseUrl } from '@/services/api'

const API_BASE = `${getApiBaseUrl()}/api/v1`

interface Universe {
  id: string
  name: string
  count: number
}

interface Ticker {
  symbol: string
  name?: string
  sector?: string
  industry?: string
  market_cap?: string
  price?: string
  recommendation?: string
  target_price?: number
  [key: string]: any
}

interface UniverseDetail extends Universe {
  tickers: Ticker[]
}

export default function UniverseManager() {
  const [universes, setUniverses] = useState<Universe[]>([])
  const [selectedUniverse, setSelectedUniverse] = useState<UniverseDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [newUniverseName, setNewUniverseName] = useState('')
  const [newTickers, setNewTickers] = useState('')
  const [editTickers, setEditTickers] = useState('')

  useEffect(() => {
    loadUniverses()
  }, [])

  const loadUniverses = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/data/universes/list`)
      if (response.ok) {
        const data = await response.json()
        setUniverses(data.universes || [])
      }
    } catch (err) {
      setError('Failed to load universes')
    } finally {
      setLoading(false)
    }
  }

  const loadUniverseDetail = async (universeId: string) => {
    try {
      const response = await fetch(`${API_BASE}/data/universe/${universeId}`)
      if (response.ok) {
        const data = await response.json()
        const detail: UniverseDetail = {
          id: universeId,
          name: universes.find(u => u.id === universeId)?.name || universeId,
          count: data.count,
          tickers: data.tickers || [],
        }
        setSelectedUniverse(detail)
        setSearchQuery('')  // Clear search when selecting new universe
        // For edit modal, just show symbols
        setEditTickers(detail.tickers.map((t: any) => t.symbol || t).join('\n'))
      }
    } catch (err) {
      setError('Failed to load universe detail')
    }
  }

  const createUniverse = async () => {
    if (!newUniverseName || !newTickers) {
      setError('Universe name and tickers required')
      return
    }

    try {
      const rawTickers = newTickers.split('\n').map(t => t.trim()).filter(t => t)
      // Remove duplicates (case-insensitive)
      const uniqueTickers = Array.from(new Set(rawTickers.map(t => t.toUpperCase())))
      const duplicateCount = rawTickers.length - uniqueTickers.length

      if (duplicateCount > 0) {
        setError(`Removed ${duplicateCount} duplicate ticker(s)`)
      }

      const response = await fetch(`${API_BASE}/data/universe/${newUniverseName}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers: uniqueTickers }),
      })

      if (response.ok) {
        setNewUniverseName('')
        setNewTickers('')
        setShowCreateModal(false)
        await loadUniverses()
        setError(null)
      } else {
        const data = await response.json()
        setError(data.error || 'Failed to create universe')
      }
    } catch (err) {
      setError('Failed to create universe')
    }
  }

  const updateUniverse = async () => {
    if (!selectedUniverse) return

    try {
      const rawTickers = editTickers.split('\n').map(t => t.trim()).filter(t => t)
      // Remove duplicates (case-insensitive)
      const uniqueTickers = Array.from(new Set(rawTickers.map(t => t.toUpperCase())))
      const duplicateCount = rawTickers.length - uniqueTickers.length

      if (duplicateCount > 0) {
        alert(`Removed ${duplicateCount} duplicate ticker(s)`)
      }

      const response = await fetch(`${API_BASE}/data/universe/${selectedUniverse.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers: uniqueTickers }),
      })

      if (response.ok) {
        setShowEditModal(false)
        await loadUniverses()
        setSelectedUniverse(null)
        setError(null)
      } else {
        const data = await response.json()
        setError(data.error || 'Failed to update universe')
      }
    } catch (err) {
      setError('Failed to update universe')
    }
  }

  const deleteUniverse = async (universeId: string) => {
    if (!confirm(`Delete universe "${universeId}"?`)) return

    try {
      const response = await fetch(`${API_BASE}/data/universe/${universeId}`, {
        method: 'DELETE',
      })

      if (response.ok) {
        await loadUniverses()
        setSelectedUniverse(null)
        setError(null)
      } else {
        const data = await response.json()
        setError(data.error || 'Failed to delete universe')
      }
    } catch (err) {
      setError('Failed to delete universe')
    }
  }

  return (
    <div className="flex-1 bg-slate-950 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Universe Manager</h1>
          <p className="text-sm text-slate-400 mt-1">Create and manage ticker universes</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium transition"
        >
          + Create Universe
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-4 p-6 overflow-hidden">
        {/* Left Panel: Universe List */}
        <div className="w-80 flex flex-col border border-slate-800 rounded-lg bg-slate-900">
          <div className="px-4 py-3 border-b border-slate-800 text-xs font-semibold text-slate-400 uppercase">
            Universes ({universes.length})
          </div>
          <div className="flex-1 overflow-y-auto px-2 py-3 space-y-2">
            {loading ? (
              <div className="text-center text-slate-500 py-8">Loading...</div>
            ) : universes.length === 0 ? (
              <div className="text-center text-slate-500 py-8">No universes</div>
            ) : (
              universes.map(uni => (
                <button
                  key={uni.id}
                  onClick={() => loadUniverseDetail(uni.id)}
                  className={`w-full text-left px-3 py-2 rounded transition ${
                    selectedUniverse?.id === uni.id
                      ? 'bg-purple-600/30 text-purple-300 border border-purple-500'
                      : 'text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  <div className="font-medium">{uni.id}</div>
                  <div className="text-xs text-slate-500">{uni.count} tickers</div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Right Panel: Universe Details */}
        <div className="flex-1 flex flex-col border border-slate-800 rounded-lg bg-slate-900 overflow-hidden">
          {selectedUniverse ? (
            <>
              {/* Detail Header */}
              <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">{selectedUniverse.id}</h2>
                  <p className="text-sm text-slate-400">{selectedUniverse.count} tickers</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setShowEditModal(true)
                      setEditTickers(selectedUniverse.tickers.join('\n'))
                    }}
                    className="px-3 py-1 bg-blue-600/20 text-blue-300 rounded text-sm hover:bg-blue-600/30 transition"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => deleteUniverse(selectedUniverse.id)}
                    className="px-3 py-1 bg-red-600/20 text-red-300 rounded text-sm hover:bg-red-600/30 transition"
                  >
                    Delete
                  </button>
                </div>
              </div>

              {/* Search Bar */}
              <div className="px-6 py-4 border-b border-slate-800">
                <input
                  type="text"
                  placeholder="Search tickers, names, sectors..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                />
              </div>

              {/* Tickers Table */}
              <div className="flex-1 overflow-auto">
                {selectedUniverse.tickers.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-slate-500">
                    No tickers in this universe
                  </div>
                ) : (
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-slate-800 border-b border-slate-700">
                      <tr>
                        <th className="px-3 py-2 text-left text-slate-300 font-semibold">Symbol</th>
                        <th className="px-3 py-2 text-left text-slate-300 font-semibold">Name</th>
                        <th className="px-3 py-2 text-left text-slate-300 font-semibold">Sector</th>
                        <th className="px-3 py-2 text-left text-slate-300 font-semibold">Industry</th>
                        <th className="px-3 py-2 text-right text-slate-300 font-semibold">Market Cap</th>
                        <th className="px-3 py-2 text-right text-slate-300 font-semibold">Price</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {selectedUniverse.tickers
                        .filter((ticker: any) => {
                          const query = searchQuery.toLowerCase()
                          return (
                            query === '' ||
                            (ticker.symbol && ticker.symbol.toLowerCase().includes(query)) ||
                            (ticker.name && ticker.name.toLowerCase().includes(query)) ||
                            (ticker.sector && ticker.sector.toLowerCase().includes(query)) ||
                            (ticker.industry && ticker.industry.toLowerCase().includes(query))
                          )
                        })
                        .map((ticker: any, idx: number) => (
                          <tr key={idx} className="hover:bg-slate-800/50 transition">
                            <td className="px-3 py-2 font-mono text-purple-300 font-medium">{ticker.symbol || ticker}</td>
                            <td className="px-3 py-2 text-slate-300">{ticker.name || ticker}</td>
                            <td className="px-3 py-2 text-slate-400">{ticker.sector || '-'}</td>
                            <td className="px-3 py-2 text-slate-400">{ticker.industry || '-'}</td>
                            <td className="px-3 py-2 text-right text-slate-400">{ticker.market_cap || '-'}</td>
                            <td className="px-3 py-2 text-right text-slate-400">{ticker.price || '-'}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                )}
              </div>

              {/* Footer with count */}
              {selectedUniverse.tickers.length > 0 && (
                <div className="px-6 py-3 border-t border-slate-800 text-xs text-slate-500">
                  Showing{' '}
                  {selectedUniverse.tickers.filter((t: any) => {
                    const query = searchQuery.toLowerCase()
                    return (
                      query === '' ||
                      (t.symbol && t.symbol.toLowerCase().includes(query)) ||
                      (t.name && t.name.toLowerCase().includes(query)) ||
                      (t.sector && t.sector.toLowerCase().includes(query)) ||
                      (t.industry && t.industry.toLowerCase().includes(query))
                    )
                  }).length}{' '}
                  of {selectedUniverse.tickers.length} tickers
                </div>
              )}
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-500">
              Select a universe to view details
            </div>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="px-6 py-3 bg-red-900/20 border-t border-red-800 text-red-400 text-sm">
          {error}
          <button
            onClick={() => setError(null)}
            className="float-right text-red-300 hover:text-red-200"
          >
            ✕
          </button>
        </div>
      )}

      {/* Create Universe Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 max-w-2xl w-full mx-4">
            <h2 className="text-xl font-bold text-white mb-4">Create Universe</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Universe Name</label>
                <input
                  type="text"
                  value={newUniverseName}
                  onChange={(e) => setNewUniverseName(e.target.value)}
                  placeholder="e.g., my_universe"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-2">Tickers (one per line)</label>
                <textarea
                  value={newTickers}
                  onChange={(e) => setNewTickers(e.target.value)}
                  placeholder="MC.PA&#10;SAF.PA&#10;OR.PA"
                  rows={10}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm font-mono focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="flex gap-3 pt-4 border-t border-slate-700">
                <button
                  onClick={createUniverse}
                  className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium transition"
                >
                  Create
                </button>
                <button
                  onClick={() => {
                    setShowCreateModal(false)
                    setNewUniverseName('')
                    setNewTickers('')
                  }}
                  className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Universe Modal */}
      {showEditModal && selectedUniverse && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 max-w-2xl w-full mx-4">
            <h2 className="text-xl font-bold text-white mb-4">Edit Universe: {selectedUniverse.id}</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Tickers (one per line)</label>
                <textarea
                  value={editTickers}
                  onChange={(e) => setEditTickers(e.target.value)}
                  rows={15}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm font-mono focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="text-xs text-slate-500">
                Total tickers: {editTickers.split('\n').filter(t => t.trim()).length}
              </div>

              <div className="flex gap-3 pt-4 border-t border-slate-700">
                <button
                  onClick={updateUniverse}
                  className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium transition"
                >
                  Update
                </button>
                <button
                  onClick={() => setShowEditModal(false)}
                  className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'

interface ScreenerItem {
  name: string
  source?: string
  tickers?: string[]
  indicators?: string[]
  formula?: string
  description?: string
}

export default function Screener() {
  const navigate = useNavigate()
  const [screeners, setScreeners] = useState<ScreenerItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
  })

  useEffect(() => {
    loadScreeners()
  }, [])

  const loadScreeners = async () => {
    try {
      setLoading(true)
      const response = await api.listScreeners()
      // Handle both array of strings and array of objects
      const screenerList = (response.screeners || []).map((item: any) =>
        typeof item === 'string' ? { name: item } : item
      )
      setScreeners(screenerList)
      setError(null)
    } catch (err) {
      setError('Failed to load screeners')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.currentTarget
    setFormData({
      ...formData,
      [name]: value,
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.createScreener({
        name: formData.name,
        description: formData.description,
      })
      resetForm()
      await loadScreeners()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create screener')
      console.error(err)
    }
  }

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete screener '${name}'?`)) return

    try {
      await api.deleteScreener(name)
      await loadScreeners()
    } catch (err) {
      setError('Failed to delete screener')
      console.error(err)
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
    })
    setShowForm(false)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Screener</h1>
          <p className="text-sm text-slate-400 mt-1">Create and manage market screeners</p>
        </div>
        <button
          onClick={() => (showForm ? resetForm() : setShowForm(true))}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition"
        >
          {showForm ? 'Cancel' : '+ New Screener'}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-900/20 border border-red-700 text-red-400 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Form */}
      {showForm && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Create New Screener</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Name */}
              <div>
                <label className="block text-sm text-slate-300 mb-2">Screener Name</label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleFormChange}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                  placeholder="e.g., tech_momentum"
                  required
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm text-slate-300 mb-2">Description</label>
                <input
                  type="text"
                  name="description"
                  value={formData.description}
                  onChange={handleFormChange}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                  placeholder="Optional description"
                />
              </div>
            </div>

            {/* Buttons */}
            <div className="flex gap-3 pt-4">
              <button
                type="submit"
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium transition"
              >
                Create
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium transition"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Screeners List */}
      <div className="space-y-3">
        {loading ? (
          <div className="text-center py-12">
            <div className="text-slate-500">Loading screeners...</div>
          </div>
        ) : screeners.length === 0 ? (
          <div className="text-center py-12 bg-slate-900 border border-slate-800 rounded-lg">
            <div className="text-slate-500">No screeners configured</div>
          </div>
        ) : (
          screeners.map((screener, idx) => (
            <div key={`${screener.name}-${idx}`} className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold text-white text-lg">{screener.name}</h3>
                  {screener.description && (
                    <p className="text-sm text-slate-400 mt-1">{screener.description}</p>
                  )}

                  <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    {screener.source && (
                      <div>
                        <div className="text-slate-500">Source</div>
                        <div className="text-slate-300">{screener.source}</div>
                      </div>
                    )}
                    {screener.tickers && screener.tickers.length > 0 && (
                      <div>
                        <div className="text-slate-500">Tickers</div>
                        <div className="text-slate-300 font-mono text-xs">
                          {screener.tickers.slice(0, 3).join(', ')}
                          {screener.tickers.length > 3 && ` +${screener.tickers.length - 3}`}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => navigate(`/screener/${screener.name}`)}
                    className="px-3 py-2 text-xs font-medium text-blue-400 hover:text-blue-300 rounded transition"
                  >
                    Open
                  </button>
                  <button
                    onClick={() => handleDelete(screener.name)}
                    className="px-3 py-2 text-xs font-medium text-red-400 hover:text-red-300 rounded transition"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

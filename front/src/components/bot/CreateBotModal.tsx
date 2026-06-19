import { useState, useEffect } from 'react'
import { api } from '@/services/api'

interface CreateBotModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function CreateBotModal({ isOpen, onClose, onSuccess }: CreateBotModalProps) {
  const [name, setName] = useState('')
  const [strategy, setStrategy] = useState('')
  const [strategies, setStrategies] = useState<{ name: string; description?: string }[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isOpen) return
    api.listStrategies()
      .then((res) => setStrategies(res.strategies || []))
      .catch(() => setStrategies([]))
  }, [isOpen])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await api.createBot({ name, strategy })
      if (response.status === 'success') {
        setName('')
        setStrategy('')
        onSuccess()
        onClose()
      } else {
        setError(response.message || 'Failed to create bot')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to create bot')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-900 rounded-lg p-8 border border-slate-800 w-full max-w-md">
        <h2 className="text-2xl font-bold text-white mb-6">Create New Bot</h2>

        {error && (
          <div className="mb-4 p-4 bg-red-900/30 border border-red-800 rounded text-red-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-slate-400 text-sm font-medium mb-2">Bot Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., cac_bot"
              required
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg focus:outline-none focus:border-purple-600"
            />
          </div>

          <div>
            <label className="block text-slate-400 text-sm font-medium mb-2">Strategy</label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              required
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white rounded-lg focus:outline-none focus:border-purple-600"
            >
              <option value="" disabled>Select a strategy...</option>
              {strategies.map((s) => (
                <option key={s.name} value={s.name}>{s.name}</option>
              ))}
            </select>
          </div>

          <div className="flex gap-4 pt-6">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !strategy}
              className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition font-medium disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Bot'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

import { useState } from 'react'
import { api } from '@/services/api'

interface CreatePortfolioModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function CreatePortfolioModal({ isOpen, onClose, onSuccess }: CreatePortfolioModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    portfolio_type: 'paper',
    currency: 'EUR',
    description: '',
    initial_capital: 100000,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await api.createPortfolio({
        name: formData.name,
        portfolio_type: formData.portfolio_type,
        currency: formData.currency,
        description: formData.description,
        initial_capital: formData.initial_capital,
      })

      if (response.status === 'success') {
        setFormData({
          name: '',
          portfolio_type: 'paper',
          currency: 'EUR',
          description: '',
          initial_capital: 100000,
        })
        onSuccess()
        onClose()
      } else {
        setError(response.message || 'Failed to create portfolio')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to create portfolio')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-900 rounded-lg p-8 border border-slate-800 w-full max-w-md">
        <h2 className="text-2xl font-bold text-white mb-6">Create New Portfolio</h2>

        {error && (
          <div className="mb-4 p-4 bg-red-900/30 border border-red-800 rounded text-red-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Portfolio Name */}
          <div>
            <label className="block text-slate-400 text-sm font-medium mb-2">Portfolio Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Growth Portfolio"
              required
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg focus:outline-none focus:border-purple-600"
            />
          </div>

          {/* Portfolio Type */}
          <div>
            <label className="block text-slate-400 text-sm font-medium mb-2">Portfolio Type</label>
            <select
              value={formData.portfolio_type}
              onChange={(e) => setFormData({ ...formData, portfolio_type: e.target.value })}
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white rounded-lg focus:outline-none focus:border-purple-600"
            >
              <option value="paper">Paper (Simulation)</option>
              <option value="real">Real Money</option>
            </select>
          </div>

          {/* Currency */}
          <div>
            <label className="block text-slate-400 text-sm font-medium mb-2">Currency</label>
            <select
              value={formData.currency}
              onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white rounded-lg focus:outline-none focus:border-purple-600"
            >
              <option value="EUR">EUR (€)</option>
              <option value="USD">USD ($)</option>
              <option value="GBP">GBP (£)</option>
            </select>
          </div>

          {/* Initial Capital */}
          <div>
            <label className="block text-slate-400 text-sm font-medium mb-2">Initial Capital</label>
            <input
              type="number"
              value={formData.initial_capital}
              onChange={(e) => setFormData({ ...formData, initial_capital: parseFloat(e.target.value) })}
              placeholder="100,000"
              min="1000"
              step="1000"
              required
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg focus:outline-none focus:border-purple-600"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-slate-400 text-sm font-medium mb-2">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Describe your portfolio strategy..."
              rows={3}
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg focus:outline-none focus:border-purple-600"
            />
          </div>

          {/* Buttons */}
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
              disabled={loading}
              className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition font-medium disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Portfolio'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { api } from '@/services/api'

interface PortfolioConfig {
  name?: string
  portfolio_type?: string
  currency?: string
  description?: string
  initial_capital?: number
  created_at?: string
  strategy?: string
}

interface Strategy {
  name: string
  description?: string
  universe?: string
  engine?: string
}

interface PortfolioSettingsProps {
  name: string
}

export default function PortfolioSettings({ name }: PortfolioSettingsProps) {
  const [config, setConfig] = useState<PortfolioConfig>({})
  const [editedConfig, setEditedConfig] = useState<PortfolioConfig>({})
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // Load portfolio config and strategies
  useEffect(() => {
    const loadConfig = async () => {
      try {
        setLoading(true)

        // Load portfolio config
        const result = await api.getPortfolioDetails(name)
        setConfig(result)
        setEditedConfig(result)

        // Load available strategies
        try {
          const strategiesResult = await api.listStrategies()
          setStrategies(strategiesResult.strategies || [])
        } catch (err) {
          console.warn('Failed to load strategies:', err)
        }

        setMessage(null)
      } catch (error) {
        console.error('Failed to load portfolio config:', error)
        setMessage({ type: 'error', text: 'Failed to load portfolio configuration' })
      } finally {
        setLoading(false)
      }
    }

    loadConfig()
  }, [name])

  const handleInputChange = (field: keyof PortfolioConfig, value: string | number) => {
    setEditedConfig(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setMessage(null)

      // Prepare update data (only send changed fields)
      const updateData: any = {}
      if (editedConfig.portfolio_type !== config.portfolio_type) {
        updateData.portfolio_type = editedConfig.portfolio_type
      }
      if (editedConfig.currency !== config.currency) {
        updateData.currency = editedConfig.currency
      }
      if (editedConfig.description !== config.description) {
        updateData.description = editedConfig.description
      }
      if (editedConfig.initial_capital !== config.initial_capital) {
        updateData.initial_capital = editedConfig.initial_capital
      }
      if (editedConfig.strategy !== config.strategy) {
        updateData.strategy = editedConfig.strategy
      }

      // Only send if there are changes
      if (Object.keys(updateData).length === 0) {
        setMessage({ type: 'success', text: 'No changes to save' })
        return
      }

      const result = await api.updatePortfolio(name, updateData)

      if (result.status === 'success') {
        setConfig(editedConfig)
        setMessage({ type: 'success', text: 'Portfolio configuration saved successfully' })
      } else {
        setMessage({ type: 'error', text: result.message || 'Failed to save portfolio configuration' })
      }
    } catch (error) {
      console.error('Failed to save portfolio config:', error)
      setMessage({ type: 'error', text: 'Failed to save portfolio configuration' })
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setEditedConfig(config)
    setMessage(null)
  }

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete portfolio "${name}"? This action cannot be undone.`)) {
      return
    }

    try {
      setSaving(true)
      setMessage(null)

      const result = await api.deletePortfolio(name)

      if (result.status === 'success') {
        setMessage({ type: 'success', text: 'Portfolio deleted successfully' })
        // Redirect to portfolios list after deletion
        setTimeout(() => {
          window.location.href = '/portfolios'
        }, 1500)
      } else {
        setMessage({ type: 'error', text: result.message || 'Failed to delete portfolio' })
      }
    } catch (error) {
      console.error('Failed to delete portfolio:', error)
      setMessage({ type: 'error', text: 'Failed to delete portfolio' })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-slate-400">Loading portfolio settings...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Message */}
      {message && (
        <div className={`p-4 rounded-lg ${
          message.type === 'success'
            ? 'bg-green-900/30 border border-green-700/50 text-green-300'
            : 'bg-red-900/30 border border-red-700/50 text-red-300'
        }`}>
          {message.text}
        </div>
      )}

      {/* Settings Form */}
      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white mb-6">Portfolio Configuration</h2>

        {/* Portfolio Name (Read-only) */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Portfolio Name</label>
          <input
            type="text"
            value={editedConfig.name || ''}
            disabled
            className="w-full px-3 py-2 bg-slate-900/50 border border-slate-600 rounded text-slate-400 text-sm"
          />
          <p className="text-xs text-slate-500 mt-1">Portfolio name cannot be changed</p>
        </div>

        {/* Portfolio Type */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Portfolio Type</label>
          <select
            value={editedConfig.portfolio_type || 'paper'}
            onChange={(e) => handleInputChange('portfolio_type', e.target.value)}
            className="w-full px-3 py-2 bg-slate-900/50 border border-slate-600 rounded text-white text-sm focus:outline-none focus:border-purple-500"
          >
            <option value="paper">Paper Trading</option>
            <option value="live">Live Trading</option>
            <option value="backtest">Backtest</option>
          </select>
        </div>

        {/* Strategy */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Strategy</label>
          <select
            value={editedConfig.strategy || ''}
            onChange={(e) => handleInputChange('strategy', e.target.value)}
            className="w-full px-3 py-2 bg-slate-900/50 border border-slate-600 rounded text-white text-sm focus:outline-none focus:border-purple-500"
          >
            <option value="">Select a strategy...</option>
            {strategies.map((strategy) => (
              <option key={strategy.name} value={strategy.name}>
                {strategy.name}
              </option>
            ))}
          </select>
        </div>

        {/* Currency */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Currency</label>
          <select
            value={editedConfig.currency || 'EUR'}
            onChange={(e) => handleInputChange('currency', e.target.value)}
            className="w-full px-3 py-2 bg-slate-900/50 border border-slate-600 rounded text-white text-sm focus:outline-none focus:border-purple-500"
          >
            <option value="EUR">EUR (€)</option>
            <option value="USD">USD ($)</option>
            <option value="GBP">GBP (£)</option>
            <option value="CHF">CHF (₣)</option>
          </select>
        </div>

        {/* Initial Capital */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Initial Capital</label>
          <input
            type="number"
            value={editedConfig.initial_capital || 0}
            onChange={(e) => handleInputChange('initial_capital', parseFloat(e.target.value))}
            className="w-full px-3 py-2 bg-slate-900/50 border border-slate-600 rounded text-white text-sm focus:outline-none focus:border-purple-500"
            step="0.01"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Description</label>
          <textarea
            value={editedConfig.description || ''}
            onChange={(e) => handleInputChange('description', e.target.value)}
            className="w-full px-3 py-2 bg-slate-900/50 border border-slate-600 rounded text-white text-sm focus:outline-none focus:border-purple-500 resize-none"
            rows={3}
            placeholder="Portfolio description"
          />
        </div>

        {/* Created Date (Read-only) */}
        {config.created_at && (
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Created</label>
            <input
              type="text"
              value={new Date(config.created_at).toLocaleDateString()}
              disabled
              className="w-full px-3 py-2 bg-slate-900/50 border border-slate-600 rounded text-slate-400 text-sm"
            />
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-600 text-white rounded-lg transition text-sm font-medium"
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
        <button
          onClick={handleCancel}
          disabled={saving}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-700 text-slate-300 rounded-lg transition text-sm font-medium"
        >
          Cancel
        </button>
        <button
          onClick={handleDelete}
          disabled={saving}
          className="px-4 py-2 bg-red-900/40 hover:bg-red-900/60 disabled:bg-slate-700 text-red-400 border border-red-700/50 rounded-lg transition text-sm font-medium ml-auto"
        >
          Delete Portfolio
        </button>
      </div>
    </div>
  )
}

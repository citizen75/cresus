import { useParams, Link, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import StrategyBuilder from '@/components/portfolio/StrategyBuilder'
import StrategyBacktests from './StrategyBacktests'
import { api } from '@/services/api'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'backtests', label: 'Backtests' },
]

export default function StrategyDetail() {
  const { name = '' } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const [showDuplicateDialog, setShowDuplicateDialog] = useState(false)
  const [newStrategyName, setNewStrategyName] = useState(`${name}_copy_1`)
  const [isDuplicating, setIsDuplicating] = useState(false)

  const getActiveTab = () => {
    if (location.pathname.includes('/backtests')) return 'backtests'
    return 'overview'
  }

  const activeTab = getActiveTab()

  const handleDuplicate = async () => {
    if (!newStrategyName.trim()) return

    setIsDuplicating(true)
    try {
      const result = await api.duplicateStrategy(name, newStrategyName)
      if (result.status === 'success') {
        setShowDuplicateDialog(false)
        setNewStrategyName('')
        // Navigate to the new strategy
        navigate(`/strategies/${encodeURIComponent(result.new_name)}`)
      }
    } catch (err) {
      console.error('Failed to duplicate strategy:', err)
      alert(`Error: ${err instanceof Error ? err.message : 'Failed to duplicate strategy'}`)
    } finally {
      setIsDuplicating(false)
    }
  }

  const handleTabChange = (tabId: string) => {
    if (tabId === 'overview') {
      navigate(`/strategies/${encodeURIComponent(name)}`)
    } else if (tabId === 'backtests') {
      navigate(`/strategies/${encodeURIComponent(name)}/backtests`)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <Link to="/strategies" className="text-purple-400 hover:text-purple-300 text-sm">
            ← Back to strategies
          </Link>
        </div>
      </div>

      {/* Strategy Header */}
      <div className="flex items-start justify-between border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-violet-600 rounded-lg flex items-center justify-center">
              <span className="text-lg">📊</span>
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white capitalize">{name}</h1>
              <p className="text-slate-400 text-sm">Strategy configuration and backtests</p>
            </div>
          </div>
        </div>
        <button
          onClick={() => setShowDuplicateDialog(true)}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded transition"
        >
          📋 Duplicate
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-slate-800">
        <div className="flex gap-8 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`px-1 py-4 font-medium text-sm transition border-b-2 whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-purple-600 text-white'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'overview' && <StrategyBuilder name={name} />}
        {activeTab === 'backtests' && <StrategyBacktests strategyName={name} />}
      </div>

      {/* Duplicate Strategy Dialog */}
      {showDuplicateDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 w-96">
            <h2 className="text-xl font-bold text-white mb-4">Duplicate Strategy</h2>
            <p className="text-slate-400 text-sm mb-4">Enter a name for the new strategy:</p>
            <input
              type="text"
              value={newStrategyName}
              onChange={(e) => setNewStrategyName(e.target.value)}
              placeholder="Strategy name"
              className="w-full bg-slate-800 border border-slate-700 text-white rounded px-3 py-2 mb-4 focus:border-purple-500 focus:outline-none"
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleDuplicate()
                if (e.key === 'Escape') setShowDuplicateDialog(false)
              }}
            />
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDuplicateDialog(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium rounded transition"
              >
                Cancel
              </button>
              <button
                onClick={handleDuplicate}
                disabled={isDuplicating || !newStrategyName.trim()}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDuplicating ? 'Duplicating...' : 'Duplicate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

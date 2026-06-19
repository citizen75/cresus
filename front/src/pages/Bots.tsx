import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useBots, useBotsSummary } from '@/hooks/useBots'
import { api } from '@/services/api'
import CreateBotModal from '@/components/bot/CreateBotModal'

export default function Bots() {
  const { data, isLoading, refetch } = useBots()
  const { data: summary, refetch: refetchSummary } = useBotsSummary()
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [deletingBot, setDeletingBot] = useState(false)
  const [togglingBot, setTogglingBot] = useState<string | null>(null)

  const bots = data?.bots || []
  const filtered = bots.filter((b: any) =>
    (b.name || '').toLowerCase().includes(searchTerm.toLowerCase())
  )

  const refreshAll = () => {
    refetch()
    refetchSummary()
  }

  const handleDelete = async (name: string) => {
    setDeletingBot(true)
    try {
      await api.deleteBot(name)
      setDeleteConfirm(null)
      refreshAll()
    } catch (error) {
      console.error('Failed to delete bot:', error)
    } finally {
      setDeletingBot(false)
    }
  }

  const handleToggleState = async (e: React.MouseEvent, name: string, currentState: string) => {
    e.stopPropagation()
    setTogglingBot(name)
    try {
      if (currentState === 'active') {
        await api.deactivateBot(name)
      } else {
        await api.activateBot(name)
      }
      refreshAll()
    } catch (error) {
      console.error('Failed to toggle bot state:', error)
    } finally {
      setTogglingBot(null)
    }
  }

  if (isLoading) {
    return <div className="text-slate-400">Loading bots...</div>
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">Bots</h1>
          <p className="text-slate-400">Automated trading bots running your strategies</p>
        </div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="px-6 py-3 bg-gradient-to-r from-purple-600 to-violet-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-violet-700 transition"
        >
          + New bot
        </button>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-3 gap-6">
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <div className="text-slate-400 text-sm mb-2">Active</div>
          <div className="text-3xl font-bold text-green-400">{summary?.active ?? 0}</div>
        </div>
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <div className="text-slate-400 text-sm mb-2">Inactive</div>
          <div className="text-3xl font-bold text-yellow-400">{summary?.inactive ?? 0}</div>
        </div>
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <div className="text-slate-400 text-sm mb-2">Total bots</div>
          <div className="text-3xl font-bold text-white">{summary?.total ?? 0}</div>
        </div>
      </div>

      {/* Search */}
      <div className="flex-1 relative">
        <input
          type="text"
          placeholder="Search bots..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-4 py-3 bg-slate-900 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-purple-600 focus:ring-1 focus:ring-purple-600"
        />
        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500">🔍</span>
      </div>

      {/* Bot Cards */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-white">Your bots ({filtered.length})</h2>

        {filtered.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            {searchTerm ? 'No bots found matching your search' : 'No bots yet'}
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map((bot: any) => {
              const isActive = bot.state === 'active'
              return (
                <div
                  key={bot.name}
                  onClick={() => navigate(`/bots/${bot.name}`)}
                  className="bg-slate-900 border border-slate-800 rounded-lg p-6 hover:border-purple-600 transition group cursor-pointer"
                >
                  <div className="grid grid-cols-12 gap-6 items-center">
                    {/* Bot Info */}
                    <div className="col-span-5">
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-violet-600 rounded-lg flex items-center justify-center flex-shrink-0">
                          <span className="text-xl">🤖</span>
                        </div>
                        <div className="flex-1">
                          <h3 className="text-white font-semibold text-lg group-hover:text-purple-400 transition">{bot.name}</h3>
                          <p className="text-slate-400 text-sm">{bot.strategy || '-'}</p>
                          <div className="flex items-center gap-2 mt-2">
                            <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                              isActive ? 'bg-green-900/30 text-green-300' : 'bg-yellow-900/30 text-yellow-300'
                            }`}>
                              {isActive ? '● Active' : '○ Inactive'}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Created */}
                    <div className="col-span-3">
                      <div className="text-slate-400 text-xs uppercase tracking-wider mb-1">Created</div>
                      <div className="text-white font-medium">{(bot.created_at || '-').slice(0, 10)}</div>
                    </div>

                    {/* Description */}
                    <div className="col-span-2">
                      <div className="text-slate-400 text-xs uppercase tracking-wider mb-1">Description</div>
                      <div className="text-slate-300 text-sm truncate">{bot.description || '-'}</div>
                    </div>

                    {/* Action Buttons */}
                    <div className="col-span-2 flex gap-2 justify-end">
                      <button
                        onClick={(e) => handleToggleState(e, bot.name, bot.state)}
                        disabled={togglingBot === bot.name}
                        className={`px-3 py-2 rounded-lg text-sm font-medium transition ${
                          isActive
                            ? 'bg-yellow-900/20 text-yellow-400 hover:bg-yellow-900/40'
                            : 'bg-green-900/20 text-green-400 hover:bg-green-900/40'
                        }`}
                      >
                        {isActive ? 'Pause' : 'Activate'}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setDeleteConfirm(bot.name)
                        }}
                        className="px-3 py-2 bg-slate-800 text-slate-400 rounded-lg hover:bg-red-900/20 hover:text-red-400 transition text-sm"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-900 rounded-lg p-8 border border-slate-800 w-full max-w-md">
            <h2 className="text-2xl font-bold text-white mb-4">Delete Bot?</h2>
            <p className="text-slate-400 mb-6">
              Are you sure you want to delete <span className="font-bold text-white">"{deleteConfirm}"</span>? This action cannot be undone.
            </p>
            <div className="flex gap-4">
              <button
                onClick={() => setDeleteConfirm(null)}
                disabled={deletingBot}
                className="flex-1 px-4 py-2 bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition font-medium disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                disabled={deletingBot}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-medium disabled:opacity-50"
              >
                {deletingBot ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Bot Modal */}
      <CreateBotModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => refreshAll()}
      />
    </div>
  )
}

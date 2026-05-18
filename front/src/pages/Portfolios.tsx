import { usePortfolios } from '@/hooks/usePortfolio'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/services/api'
import CreatePortfolioModal from '@/components/portfolio/CreatePortfolioModal'
import { formatCurrency } from '@/utils/currency'

export default function Portfolios() {
  const { data, isLoading, refetch } = usePortfolios()
  const [searchTerm, setSearchTerm] = useState('')
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [deletingPortfolio, setDeletingPortfolio] = useState(false)

  const portfolios = data?.portfolios || []
  const livePortfolios = portfolios.filter(p => p.type === 'real')
  const filtered = livePortfolios.filter(p =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // Calculate metrics from real portfolios only
  const totalNetWorth = livePortfolios.reduce((sum, p) => sum + (p.total_portfolio_value || 0), 0)
  const totalInvested = livePortfolios.reduce((sum, p) => sum + (p.initial_capital || 0), 0)
  const totalGain = totalNetWorth - totalInvested
  const totalGainPercent = totalInvested > 0 ? (totalGain / totalInvested * 100) : 0

  const handleDelete = async (name: string) => {
    setDeletingPortfolio(true)
    try {
      await api.deletePortfolio(name)
      setDeleteConfirm(null)
      refetch()
    } catch (error) {
      console.error('Failed to delete portfolio:', error)
    } finally {
      setDeletingPortfolio(false)
    }
  }

  if (isLoading) {
    return <div className="text-slate-400">Loading portfolios...</div>
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">Portfolios</h1>
          <p className="text-slate-400">Overview of all your investment portfolios</p>
        </div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="px-6 py-3 bg-gradient-to-r from-purple-600 to-violet-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-violet-700 transition"
        >
          + New portfolio
        </button>
      </div>

      {/* Summary Metrics */}
      {(() => {
        // Use first portfolio's currency or default to USD
        const displayCurrency = livePortfolios.length > 0 ? (livePortfolios[0].currency || 'USD') : 'USD'

        return (
          <div className="grid grid-cols-4 gap-6">
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <div className="text-slate-400 text-sm mb-2">Total net worth</div>
              <div className="text-3xl font-bold text-white">{formatCurrency(totalNetWorth, displayCurrency)}</div>
              <div className={`${totalGain >= 0 ? 'text-green-400' : 'text-red-400'} text-sm mt-2`}>
                {totalGain >= 0 ? '+' : ''}{formatCurrency(Math.abs(totalGain), displayCurrency)} ({totalGainPercent >= 0 ? '+' : ''}{totalGainPercent.toFixed(2)}%)
              </div>
            </div>
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <div className="text-slate-400 text-sm mb-2">Today's change</div>
              <div className={`text-3xl font-bold ${totalGain >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {totalGain >= 0 ? '+' : ''}{formatCurrency(Math.abs(totalGain), displayCurrency)}
              </div>
              <div className={`${totalGain >= 0 ? 'text-green-400' : 'text-red-400'} text-sm mt-2`}>
                {totalGainPercent >= 0 ? '+' : ''}{totalGainPercent.toFixed(2)}%
              </div>
            </div>
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <div className="text-slate-400 text-sm mb-2">YTD return (weighted)</div>
              <div className={`text-3xl font-bold ${totalGainPercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {totalGainPercent >= 0 ? '+' : ''}{totalGainPercent.toFixed(2)}%
              </div>
              <div className="text-slate-400 text-sm mt-2">from {livePortfolios.length} {livePortfolios.length === 1 ? 'portfolio' : 'portfolios'}</div>
            </div>
            <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
              <div className="text-slate-400 text-sm mb-2">Total portfolios</div>
              <div className="text-3xl font-bold text-white">{livePortfolios.length}</div>
              <div className="text-slate-400 text-sm mt-2">{livePortfolios.length} active</div>
            </div>
          </div>
        )
      })()}

      {/* Search and Filter */}
      <div className="flex items-center justify-between gap-6">
        <div className="flex-1 relative">
          <input
            type="text"
            placeholder="Search portfolios..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-4 py-3 bg-slate-900 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-purple-600 focus:ring-1 focus:ring-purple-600"
          />
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500">🔍</span>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-3 bg-slate-900 border border-slate-800 rounded-lg text-slate-300 hover:bg-slate-800 transition font-medium">
            Sort by: Total value
          </button>
          <button className="px-4 py-3 bg-slate-900 border border-slate-800 rounded-lg text-slate-300 hover:bg-slate-800 transition">
            Filters
          </button>
        </div>
      </div>

      {/* Portfolio Cards */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-white">Your portfolios ({filtered.length})</h2>

        {filtered.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            {searchTerm ? 'No portfolios found matching your search' : 'No portfolios yet'}
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map((portfolio) => (
              <div key={portfolio.name} className="bg-slate-900 border border-slate-800 rounded-lg p-6 hover:border-purple-600 transition group">
                <div className="grid grid-cols-12 gap-6 items-center">
                  {/* Portfolio Info */}
                  <div className="col-span-3">
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-violet-600 rounded-lg flex items-center justify-center flex-shrink-0">
                        <span className="text-xl">💼</span>
                      </div>
                      <div className="flex-1">
                        <h3 className="text-white font-semibold text-lg group-hover:text-purple-400 transition">{portfolio.name}</h3>
                        <p className="text-slate-400 text-sm capitalize">{portfolio.type} portfolio</p>
                        <div className="flex items-center gap-2 mt-2">
                          <span className="inline-flex px-2 py-1 rounded bg-purple-900/30 text-purple-300 text-xs font-medium">
                            {portfolio.type === 'paper' ? '📄 Paper' : '💰 Real'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Value */}
                  <div className="col-span-2">
                    <div className="text-slate-400 text-xs uppercase tracking-wider mb-1">Total value</div>
                    <div className="text-white font-bold text-lg">{formatCurrency(portfolio.total_portfolio_value || 0, portfolio.currency || 'USD')}</div>
                    <div className={`text-sm ${(portfolio.unrealized_gain || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {(portfolio.unrealized_gain || 0) >= 0 ? '+' : ''}{formatCurrency(Math.abs(portfolio.unrealized_gain || 0), portfolio.currency || 'USD')} ({(portfolio.unrealized_gain_pct || 0).toFixed(2)}%)
                    </div>
                  </div>

                  {/* Invested */}
                  <div className="col-span-2">
                    <div className="text-slate-400 text-xs uppercase tracking-wider mb-1">Invested</div>
                    <div className="text-white font-bold text-lg">{formatCurrency(portfolio.total_positions_value || 0, portfolio.currency || 'USD')}</div>
                    <div className="text-slate-400 text-sm">
                      {((portfolio.total_positions_value || 0) / (portfolio.total_portfolio_value || 1) * 100).toFixed(1)}% of portfolio
                    </div>
                  </div>

                  {/* Cash */}
                  <div className="col-span-2">
                    <div className="text-slate-400 text-xs uppercase tracking-wider mb-1">Cash</div>
                    <div className="text-white font-bold text-lg">{formatCurrency(portfolio.cash || 0, portfolio.currency || 'USD')}</div>
                    <div className="text-slate-400 text-sm">
                      {((portfolio.cash || 0) / (portfolio.total_portfolio_value || 1) * 100).toFixed(1)}% of portfolio
                    </div>
                  </div>

                  {/* Positions */}
                  <div className="col-span-2">
                    <div className="text-slate-400 text-xs uppercase tracking-wider mb-1">Positions</div>
                    <div className="text-white font-bold text-lg">{portfolio.num_positions}</div>
                    <div className="text-slate-400 text-sm">{portfolio.num_trades} trades</div>
                  </div>

                  {/* Action Buttons */}
                  <div className="col-span-1 flex gap-2 justify-end">
                    <Link
                      to={`/portfolios/${portfolio.name}`}
                      className="px-4 py-2 bg-gradient-to-r from-purple-600 to-violet-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-violet-700 transition text-sm"
                    >
                      Open
                    </Link>
                    <button
                      onClick={() => setDeleteConfirm(portfolio.name)}
                      className="px-3 py-2 bg-slate-800 text-slate-400 rounded-lg hover:bg-red-900/20 hover:text-red-400 transition text-sm"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-900 rounded-lg p-8 border border-slate-800 w-full max-w-md">
            <h2 className="text-2xl font-bold text-white mb-4">Delete Portfolio?</h2>
            <p className="text-slate-400 mb-6">
              Are you sure you want to delete <span className="font-bold text-white">"{deleteConfirm}"</span>? This action cannot be undone.
            </p>
            <div className="flex gap-4">
              <button
                onClick={() => setDeleteConfirm(null)}
                disabled={deletingPortfolio}
                className="flex-1 px-4 py-2 bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition font-medium disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                disabled={deletingPortfolio}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-medium disabled:opacity-50"
              >
                {deletingPortfolio ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Portfolio Modal */}
      <CreatePortfolioModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => refetch()}
      />
    </div>
  )
}

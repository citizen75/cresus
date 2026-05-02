import { useState, useEffect } from 'react'
import { api } from '@/services/api'

interface TransactionsViewProps {
  name: string
  filterTicker?: string
}

interface Transaction {
  id: string
  created_at: string
  operation: string
  ticker: string
  quantity: number
  price: number
  amount: number
  fees: number
  status: string
  status_at: string
  notes: string
}

export default function TransactionsView({ name, filterTicker }: TransactionsViewProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editData, setEditData] = useState<any>(null)
  const [isUpdating, setIsUpdating] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const itemsPerPage = 10

  useEffect(() => {
    loadTransactions()
  }, [name, filterTicker])

  const loadTransactions = async () => {
    setIsLoading(true)
    setError('')
    try {
      const data = await api.getTransactions(name, filterTicker)
      setTransactions(data.transactions || [])
    } catch (err: any) {
      setError(err.message || 'Failed to load transactions')
    } finally {
      setIsLoading(false)
    }
  }

  const handleEdit = (transaction: Transaction) => {
    setEditingId(transaction.id)
    setEditData({
      created_at: transaction.created_at,
      quantity: transaction.quantity,
      price: transaction.price,
      fees: transaction.fees,
      notes: transaction.notes,
    })
  }

  const handleSaveEdit = async (id: string) => {
    setIsUpdating(true)
    try {
      await api.updateTransaction(name, id, editData)
      setEditingId(null)
      loadTransactions()
    } catch (err: any) {
      setError(err.message || 'Failed to update transaction')
    } finally {
      setIsUpdating(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await api.deleteTransaction(name, id)
      setDeleteConfirm(null)
      loadTransactions()
    } catch (err: any) {
      setError(err.message || 'Failed to delete transaction')
    }
  }

  if (isLoading) {
    return <div className="text-slate-400 py-8 text-center">Loading transactions...</div>
  }

  const totalPages = Math.ceil(transactions.length / itemsPerPage)
  const paginatedTransactions = transactions.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Transactions</h2>
          <p className="text-slate-400 text-sm mt-1">
            {filterTicker ? `Transactions for ${filterTicker}` : 'All transactions'}
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-900/30 border border-red-800 rounded text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Transactions Table */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
        {transactions.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            No transactions found
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-800/50 border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3 text-left text-slate-400 font-medium">Date</th>
                    <th className="px-4 py-3 text-left text-slate-400 font-medium">Operation</th>
                    <th className="px-4 py-3 text-left text-slate-400 font-medium">Ticker</th>
                    <th className="px-4 py-3 text-left text-slate-400 font-medium">Qty</th>
                    <th className="px-4 py-3 text-left text-slate-400 font-medium">Price</th>
                    <th className="px-4 py-3 text-left text-slate-400 font-medium">Amount</th>
                    <th className="px-4 py-3 text-left text-slate-400 font-medium">Fees</th>
                    <th className="px-4 py-3 text-left text-slate-400 font-medium">Notes</th>
                    <th className="px-4 py-3 text-left text-slate-400 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedTransactions.map((tx: Transaction) => (
                    <tr key={tx.id} className="border-t border-slate-800 hover:bg-slate-800/30 transition">
                      <td className="px-4 py-3 text-slate-300 text-sm">
                        {editingId === tx.id ? (
                          <input
                            type="date"
                            value={editData.created_at.split('T')[0]}
                            onChange={(e) => {
                              const dateStr = e.target.value
                              const fullDateTime = `${dateStr}T${editData.created_at.split('T')[1] || '00:00:00'}`
                              setEditData({ ...editData, created_at: fullDateTime })
                            }}
                            className="w-32 px-2 py-1 bg-slate-700 border border-slate-600 text-white rounded"
                          />
                        ) : (
                          new Date(tx.created_at).toLocaleDateString('de-DE')
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                            tx.operation === 'BUY'
                              ? 'bg-green-900/30 text-green-400'
                              : 'bg-red-900/30 text-red-400'
                          }`}
                        >
                          {tx.operation}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-white font-medium">{tx.ticker}</td>
                      <td className="px-4 py-3 text-white">
                        {editingId === tx.id ? (
                          <input
                            type="number"
                            value={editData.quantity}
                            onChange={(e) => setEditData({ ...editData, quantity: parseInt(e.target.value) })}
                            className="w-16 px-2 py-1 bg-slate-700 border border-slate-600 text-white rounded"
                          />
                        ) : (
                          tx.quantity
                        )}
                      </td>
                      <td className="px-4 py-3 text-white">
                        {editingId === tx.id ? (
                          <input
                            type="number"
                            step="0.01"
                            value={editData.price}
                            onChange={(e) => setEditData({ ...editData, price: parseFloat(e.target.value) })}
                            className="w-20 px-2 py-1 bg-slate-700 border border-slate-600 text-white rounded"
                          />
                        ) : (
                          `€${tx.price.toLocaleString('de-DE', { maximumFractionDigits: 2 })}`
                        )}
                      </td>
                      <td className="px-4 py-3 text-white font-medium">
                        €{tx.amount.toLocaleString('de-DE', { maximumFractionDigits: 2 })}
                      </td>
                      <td className="px-4 py-3 text-orange-400">
                        {editingId === tx.id ? (
                          <input
                            type="number"
                            step="0.01"
                            value={editData.fees}
                            onChange={(e) => setEditData({ ...editData, fees: parseFloat(e.target.value) })}
                            className="w-16 px-2 py-1 bg-slate-700 border border-slate-600 text-white rounded"
                          />
                        ) : (
                          `€${tx.fees.toLocaleString('de-DE', { maximumFractionDigits: 2 })}`
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-300 text-sm max-w-xs truncate">
                        {editingId === tx.id ? (
                          <input
                            type="text"
                            value={editData.notes}
                            onChange={(e) => setEditData({ ...editData, notes: e.target.value })}
                            className="w-full px-2 py-1 bg-slate-700 border border-slate-600 text-white rounded"
                          />
                        ) : (
                          tx.notes
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {editingId === tx.id ? (
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleSaveEdit(tx.id)}
                              disabled={isUpdating}
                              className="px-2 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-xs disabled:opacity-50"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingId(null)}
                              className="px-2 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded text-xs"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleEdit(tx)}
                              className="text-blue-400 hover:text-blue-300 transition text-sm"
                            >
                              ✏️
                            </button>
                            <button
                              onClick={() => setDeleteConfirm(tx.id)}
                              className="text-red-400 hover:text-red-300 transition text-sm"
                            >
                              🗑️
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="px-6 py-4 border-t border-slate-800 bg-slate-900 flex items-center justify-between text-sm">
              <p className="text-slate-400">
                Showing {Math.min((currentPage - 1) * itemsPerPage + 1, transactions.length)}-
                {Math.min(currentPage * itemsPerPage, transactions.length)} of {transactions.length} transactions
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="px-2 py-1 bg-slate-800 border border-slate-700 text-slate-300 rounded hover:bg-slate-700 disabled:opacity-50 transition"
                >
                  ←
                </button>
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => i + 1).map((page) => (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page)}
                    className={`px-2 py-1 rounded transition ${
                      page === currentPage
                        ? 'bg-purple-600 text-white'
                        : 'bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    {page}
                  </button>
                ))}
                <button
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                  className="px-2 py-1 bg-slate-800 border border-slate-700 text-slate-300 rounded hover:bg-slate-700 disabled:opacity-50 transition"
                >
                  →
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-900 rounded-lg p-8 border border-slate-800 w-full max-w-md">
            <h2 className="text-2xl font-bold text-white mb-4">Delete Transaction?</h2>
            <p className="text-slate-400 mb-6">
              Are you sure you want to delete this transaction? This action cannot be undone.
            </p>
            <div className="flex gap-4">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="flex-1 px-4 py-2 bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition font-medium"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-medium"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

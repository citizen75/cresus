import { useState, useEffect } from 'react'
import { api } from '@/services/api'

interface PositionModalProps {
  isOpen: boolean
  mode: 'buy' | 'sell' | null
  ticker?: string
  positionData?: any
  onClose: () => void
  onSuccess: () => void
  portfolioName: string
}

export default function PositionModal({ isOpen, mode, ticker, positionData, onClose, onSuccess, portfolioName }: PositionModalProps) {
  const [formData, setFormData] = useState({
    ticker: ticker || '',
    quantity: '',
    price: '',
    fees: '',
    date: new Date().toISOString().split('T')[0],
    notes: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (mode === 'buy' || mode === 'sell') {
      setFormData({
        ticker: ticker || '',
        quantity: '',
        price: '',
        fees: '',
        date: new Date().toISOString().split('T')[0],
        notes: '',
      })
    }
  }, [mode, ticker])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const operation = mode === 'buy' ? 'BUY' : 'SELL'
      const response = await api.recordTransaction(portfolioName, {
        operation,
        ticker: formData.ticker,
        quantity: parseInt(formData.quantity),
        price: parseFloat(formData.price),
        fees: formData.fees ? parseFloat(formData.fees) : 0,
        notes: formData.notes,
      })

      if (response.status === 'success') {
        setFormData({
          ticker: '',
          quantity: '',
          price: '',
          fees: '',
          date: new Date().toISOString().split('T')[0],
          notes: '',
        })
        onSuccess()
        onClose()
      } else {
        setError(response.message || 'Failed to record transaction')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to complete transaction')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen || !mode) return null

  const title = mode === 'buy' ? 'Buy Position' : 'Sell Position'
  const submitText = mode === 'buy' ? 'Buy' : 'Sell'
  const submitColor = mode === 'sell' ? 'bg-red-600 hover:bg-red-700' : 'bg-purple-600 hover:bg-purple-700'

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-900 rounded-lg p-8 border border-slate-800 w-full max-w-md">
        <h2 className="text-2xl font-bold text-white mb-6">{title}</h2>

        {error && (
          <div className="mb-4 p-4 bg-red-900/30 border border-red-800 rounded text-red-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Ticker */}
          <div>
            <label className="block text-slate-400 text-sm font-medium mb-2">Ticker</label>
            <input
              type="text"
              value={formData.ticker}
              onChange={(e) => setFormData({ ...formData, ticker: e.target.value.toUpperCase() })}
              placeholder="e.g., AAPL"
              required
              disabled={mode === 'sell'}
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg focus:outline-none focus:border-purple-600 disabled:opacity-50"
            />
          </div>

          {/* Quantity */}
          <div>
            <label className="block text-slate-400 text-sm font-medium mb-2">Quantity (Shares)</label>
            <input
              type="number"
              value={formData.quantity}
              onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
              placeholder="100"
              min="1"
              required
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg focus:outline-none focus:border-purple-600"
            />
          </div>

          {/* Price */}
          <div>
            <label className="block text-slate-400 text-sm font-medium mb-2">Price per Share (€)</label>
            <input
              type="number"
              value={formData.price}
              onChange={(e) => setFormData({ ...formData, price: e.target.value })}
              placeholder="150.50"
              min="0.01"
              step="0.01"
              required
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg focus:outline-none focus:border-purple-600"
            />
          </div>

          {/* Fees */}
          <div>
            <label className="block text-slate-400 text-sm font-medium mb-2">Fees (€) - Optional</label>
            <input
              type="number"
              value={formData.fees}
              onChange={(e) => setFormData({ ...formData, fees: e.target.value })}
              placeholder="0.00"
              min="0"
              step="0.01"
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg focus:outline-none focus:border-purple-600"
            />
          </div>

          {/* Date */}
          <div>
            <label className="block text-slate-400 text-sm font-medium mb-2">Date</label>
            <input
              type="date"
              value={formData.date}
              onChange={(e) => setFormData({ ...formData, date: e.target.value })}
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white rounded-lg focus:outline-none focus:border-purple-600"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-slate-400 text-sm font-medium mb-2">Notes (Optional)</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Add notes about this transaction..."
              rows={3}
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg focus:outline-none focus:border-purple-600"
            />
          </div>

          {/* Summary */}
          {formData.quantity && formData.price && (
            <div className="bg-slate-800/50 rounded p-4 space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Position Value:</span>
                <span className="text-white">
                  €{(parseFloat(formData.quantity) * parseFloat(formData.price)).toLocaleString('de-DE', { maximumFractionDigits: 2 })}
                </span>
              </div>
              {formData.fees && parseFloat(formData.fees) > 0 && (
                <div className="flex justify-between">
                  <span className="text-slate-400">Fees:</span>
                  <span className="text-orange-400">
                    €{parseFloat(formData.fees).toLocaleString('de-DE', { maximumFractionDigits: 2 })}
                  </span>
                </div>
              )}
              <div className="flex justify-between pt-2 border-t border-slate-700">
                <span className="text-slate-300 font-medium">Total Cost:</span>
                <span className="text-white font-bold">
                  €{(
                    parseFloat(formData.quantity) * parseFloat(formData.price) +
                    (formData.fees ? parseFloat(formData.fees) : 0)
                  ).toLocaleString('de-DE', { maximumFractionDigits: 2 })}
                </span>
              </div>
            </div>
          )}

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
              className={`flex-1 px-4 py-2 ${submitColor} text-white rounded-lg transition font-medium disabled:opacity-50`}
            >
              {loading ? 'Processing...' : submitText}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

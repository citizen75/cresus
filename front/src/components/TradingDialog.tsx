import { useState } from 'react'
import { formatCurrency } from '@/utils/currency'

interface TradingDialogProps {
  isOpen: boolean
  mode: 'buy' | 'sell'
  ticker: string
  position?: any
  currentPrice?: number
  onClose: () => void
  onConfirm: (quantity: number, price?: number, fees?: number, stopLoss?: number, takeProfit?: number) => void
}

export function TradingDialog({
  isOpen,
  mode,
  ticker,
  position,
  currentPrice = 0,
  onClose,
  onConfirm,
}: TradingDialogProps) {
  const [quantity, setQuantity] = useState<string>('')
  const [priceOverride, setPriceOverride] = useState<string>('')
  const [fees, setFees] = useState<string>('0')
  const [stopLoss, setStopLoss] = useState<string>('')
  const [takeProfit, setTakeProfit] = useState<string>('')

  const handleConfirm = () => {
    const qty = parseFloat(quantity)
    if (isNaN(qty) || qty <= 0) {
      alert('Please enter a valid quantity')
      return
    }

    const price = priceOverride ? parseFloat(priceOverride) : undefined
    if (priceOverride && (isNaN(price!) || price! <= 0)) {
      alert('Please enter a valid price')
      return
    }

    const feesAmount = parseFloat(fees || '0')
    const sl = stopLoss ? parseFloat(stopLoss) : undefined
    const tp = takeProfit ? parseFloat(takeProfit) : undefined

    if (sl !== undefined && isNaN(sl)) {
      alert('Please enter a valid stop loss')
      return
    }

    if (tp !== undefined && isNaN(tp)) {
      alert('Please enter a valid take profit')
      return
    }

    onConfirm(qty, price, feesAmount, sl, tp)
    setQuantity('')
    setPriceOverride('')
    setFees('0')
    setStopLoss('')
    setTakeProfit('')
  }

  if (!isOpen) return null

  const price = priceOverride ? parseFloat(priceOverride) : currentPrice
  const total = price * parseFloat(quantity || '0')
  const currentHoldings = position?.quantity || 0

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white">
            {mode === 'buy' ? '📈 Buy' : '📉 Sell'} {ticker}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 text-xl"
          >
            ✕
          </button>
        </div>

        {/* Current Price */}
        <div className="bg-slate-800/50 rounded p-3 mb-4">
          <div className="text-sm text-slate-400">Current Price</div>
          <div className="text-lg font-bold text-white">{formatCurrency(currentPrice)}</div>
        </div>

        {/* Holdings Info (for sell) */}
        {mode === 'sell' && (
          <div className="bg-slate-800/50 rounded p-3 mb-4">
            <div className="text-sm text-slate-400">Current Holdings</div>
            <div className="text-lg font-bold text-white">{currentHoldings} shares</div>
          </div>
        )}

        {/* Quantity Input */}
        <div className="mb-4">
          <label className="block text-sm text-slate-400 mb-2">Quantity</label>
          <input
            type="number"
            min="0"
            step="0.01"
            placeholder="Enter quantity"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded focus:outline-none focus:border-purple-600"
          />
        </div>

        {/* Price Override Input */}
        <div className="mb-4">
          <label className="block text-sm text-slate-400 mb-2">Price (optional)</label>
          <input
            type="number"
            min="0"
            step="0.01"
            placeholder="Leave blank for current price"
            value={priceOverride}
            onChange={(e) => setPriceOverride(e.target.value)}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded focus:outline-none focus:border-purple-600"
          />
        </div>

        {/* Total */}
        {quantity && (
          <div className="bg-slate-800/50 rounded p-3 mb-4">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Total</span>
              <span className={`text-lg font-bold ${total > 0 ? 'text-white' : 'text-slate-500'}`}>
                {formatCurrency(total)}
              </span>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium transition"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className={`flex-1 px-4 py-2 rounded font-medium transition text-white ${
              mode === 'buy'
                ? 'bg-green-600 hover:bg-green-700'
                : 'bg-red-600 hover:bg-red-700'
            }`}
          >
            {mode === 'buy' ? 'Buy' : 'Sell'}
          </button>
        </div>
      </div>
    </div>
  )
}

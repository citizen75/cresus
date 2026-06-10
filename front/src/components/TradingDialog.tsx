import { useState, useEffect } from 'react'
import { formatCurrency } from '@/utils/currency'
import { api } from '@/services/api'

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
  ticker: initialTicker,
  position,
  currentPrice: initialPrice = 0,
  onClose,
  onConfirm,
}: TradingDialogProps) {
  const [ticker, setTicker] = useState(initialTicker || '')
  const [tickerName, setTickerName] = useState('')
  const [price, setPrice] = useState<string>(initialPrice ? initialPrice.toString() : '')
  const [quantity, setQuantity] = useState<string>('')
  const [fees, setFees] = useState<string>('0')
  const [stopLoss, setStopLoss] = useState<string>('7')
  const [takeProfit, setTakeProfit] = useState<string>('2')
  const [loadingTicker, setLoadingTicker] = useState(false)

  // Fetch ticker name when ticker changes
  useEffect(() => {
    if (ticker && ticker !== initialTicker) {
      fetchTickerName(ticker)
    } else if (ticker === initialTicker && initialTicker) {
      setTickerName(position?.company_name || '')
    }
  }, [ticker])

  // Set initial ticker if provided
  useEffect(() => {
    if (initialTicker && !ticker) {
      setTicker(initialTicker)
      setTickerName(position?.company_name || '')
    }
  }, [initialTicker])

  const fetchTickerName = async (tickerSymbol: string) => {
    try {
      setLoadingTicker(true)
      const response = await api.getTickerInfo?.(tickerSymbol)
      if (response?.name) {
        setTickerName(response.name)
      }
    } catch (err) {
      console.error('Failed to fetch ticker info:', err)
    } finally {
      setLoadingTicker(false)
    }
  }

  const handleConfirm = () => {
    if (!ticker) {
      alert('Please enter a ticker')
      return
    }

    const qty = parseFloat(quantity)
    if (isNaN(qty) || qty <= 0) {
      alert('Please enter a valid quantity')
      return
    }

    const priceVal = parseFloat(price || String(initialPrice))
    if (isNaN(priceVal) || priceVal <= 0) {
      alert('Please enter a valid price')
      return
    }

    const feesVal = parseFloat(fees || '0')
    const stopVal = parseFloat(stopLoss || '0') / 100 // Convert percentage to decimal
    const targetVal = parseFloat(takeProfit || '0') / 100 // Convert percentage to decimal

    onConfirm(qty, priceVal, feesVal, stopVal, targetVal)
    resetForm()
  }

  const resetForm = () => {
    setTicker(initialTicker || '')
    setPrice(initialPrice ? initialPrice.toString() : '')
    setQuantity('')
    setFees('0')
    setStopLoss('7')
    setTakeProfit('2')
  }

  if (!isOpen) return null

  const priceVal = parseFloat(price || String(initialPrice)) || 0
  const qtyVal = parseFloat(quantity || '0') || 0
  const feesVal = parseFloat(fees || '0') || 0
  const totalAmount = qtyVal * priceVal - feesVal
  const currentHoldings = position?.quantity || 0

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white">
            {mode === 'buy' ? '📈 Buy' : '📉 Sell'} {ticker || '...'}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 text-xl"
          >
            ✕
          </button>
        </div>

        {/* Ticker Input */}
        <div className="mb-4">
          <label className="block text-sm text-slate-400 mb-2">Ticker</label>
          <input
            type="text"
            placeholder="e.g., AAPL, AF.PA"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            disabled={initialTicker ? true : false}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded focus:outline-none focus:border-purple-600 disabled:opacity-50"
          />
          {tickerName && <p className="text-xs text-slate-400 mt-1">📊 {tickerName}</p>}
          {loadingTicker && <p className="text-xs text-slate-500 mt-1">Loading...</p>}
        </div>

        {/* Current Price */}
        <div className="bg-slate-800/50 rounded p-3 mb-4">
          <div className="text-sm text-slate-400">Current Price</div>
          <div className="text-lg font-bold text-white">{formatCurrency(initialPrice)}</div>
        </div>

        {/* Holdings Info (for sell) */}
        {mode === 'sell' && (
          <div className="bg-slate-800/50 rounded p-3 mb-4">
            <div className="text-sm text-slate-400">Current Holdings</div>
            <div className="text-lg font-bold text-white">{currentHoldings} shares</div>
          </div>
        )}

        {/* Price Input */}
        <div className="mb-4">
          <label className="block text-sm text-slate-400 mb-2">Price</label>
          <input
            type="number"
            min="0"
            step="0.01"
            placeholder={`Default: ${initialPrice}`}
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded focus:outline-none focus:border-purple-600"
          />
        </div>

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

        {/* Fees Input */}
        <div className="mb-4">
          <label className="block text-sm text-slate-400 mb-2">Fees</label>
          <input
            type="number"
            min="0"
            step="0.01"
            placeholder="0.00"
            value={fees}
            onChange={(e) => setFees(e.target.value)}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded focus:outline-none focus:border-purple-600"
          />
        </div>

        {/* Stop Loss Input */}
        <div className="mb-4">
          <label className="block text-sm text-slate-400 mb-2">Stop Loss (%)</label>
          <input
            type="number"
            min="0"
            step="0.1"
            placeholder="7"
            value={stopLoss}
            onChange={(e) => setStopLoss(e.target.value)}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded focus:outline-none focus:border-purple-600"
          />
          {stopLoss && priceVal > 0 && (
            <p className="text-xs text-slate-500 mt-1">
              Stop at: €{(priceVal * (1 - parseFloat(stopLoss) / 100)).toFixed(2)}
            </p>
          )}
        </div>

        {/* Take Profit Input */}
        <div className="mb-4">
          <label className="block text-sm text-slate-400 mb-2">Target Profit (%)</label>
          <input
            type="number"
            min="0"
            step="0.1"
            placeholder="2"
            value={takeProfit}
            onChange={(e) => setTakeProfit(e.target.value)}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded focus:outline-none focus:border-purple-600"
          />
          {takeProfit && priceVal > 0 && (
            <p className="text-xs text-slate-500 mt-1">
              Target at: €{(priceVal * (1 + parseFloat(takeProfit) / 100)).toFixed(2)}
            </p>
          )}
        </div>

        {/* Total Amount */}
        {quantity && (
          <div className="bg-slate-800/50 rounded p-3 mb-4">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Total Amount</span>
              <span className={`text-lg font-bold ${totalAmount > 0 ? 'text-green-400' : 'text-slate-500'}`}>
                {formatCurrency(totalAmount)}
              </span>
            </div>
            {fees && parseFloat(fees) > 0 && (
              <div className="flex justify-between items-center text-xs text-slate-500 mt-2">
                <span>({qtyVal} × €{priceVal.toFixed(2)} - €{feesVal.toFixed(2)})</span>
              </div>
            )}
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

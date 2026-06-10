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
  const [price, setPrice] = useState<string>(String(initialPrice || ''))
  const [quantity, setQuantity] = useState<string>('')
  const [fees, setFees] = useState<string>('0')
  const [stopLoss, setStopLoss] = useState<string>('7') // Default 7%
  const [takeProfit, setTakeProfit] = useState<string>('2') // Default 2%
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
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 max-w-sm w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold text-white">
            {mode === 'buy' ? '📈' : '📉'} {ticker || '...'}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">✕</button>
        </div>

        {/* Price & Holdings */}
        <div className="grid grid-cols-2 gap-2 mb-3 text-xs">
          <div className="bg-slate-800/50 rounded p-2">
            <div className="text-slate-400">Price</div>
            <div className="font-bold text-white">{formatCurrency(initialPrice)}</div>
          </div>
          {mode === 'sell' && (
            <div className="bg-slate-800/50 rounded p-2">
              <div className="text-slate-400">Holdings</div>
              <div className="font-bold text-white">{currentHoldings}</div>
            </div>
          )}
        </div>

        {/* Inputs Grid */}
        <div className="space-y-2 mb-3">
          {!initialTicker && (
            <div>
              <label className="text-xs text-slate-400">Ticker</label>
              <input
                type="text"
                placeholder="AAPL"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className="w-full px-2 py-1 bg-slate-800 border border-slate-700 text-white text-sm rounded focus:outline-none focus:border-purple-600"
              />
              {tickerName && <p className="text-xs text-slate-500">{tickerName}</p>}
            </div>
          )}

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-slate-400">Price</label>
              <input
                type="number"
                step="0.01"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="w-full px-2 py-1 bg-slate-800 border border-slate-700 text-white text-sm rounded focus:outline-none focus:border-purple-600"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Qty</label>
              <input
                type="number"
                step="0.01"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="w-full px-2 py-1 bg-slate-800 border border-slate-700 text-white text-sm rounded focus:outline-none focus:border-purple-600"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="text-xs text-slate-400">Fees</label>
              <input
                type="number"
                step="0.01"
                value={fees}
                onChange={(e) => setFees(e.target.value)}
                className="w-full px-2 py-1 bg-slate-800 border border-slate-700 text-white text-sm rounded focus:outline-none focus:border-purple-600"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Stop %</label>
              <input
                type="number"
                step="0.1"
                value={stopLoss}
                onChange={(e) => setStopLoss(e.target.value)}
                className="w-full px-2 py-1 bg-slate-800 border border-slate-700 text-white text-sm rounded focus:outline-none focus:border-purple-600"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Target %</label>
              <input
                type="number"
                step="0.1"
                value={takeProfit}
                onChange={(e) => setTakeProfit(e.target.value)}
                className="w-full px-2 py-1 bg-slate-800 border border-slate-700 text-white text-sm rounded focus:outline-none focus:border-purple-600"
              />
            </div>
          </div>
        </div>

        {/* Calculations */}
        {priceVal > 0 && (
          <div className="bg-slate-800/30 rounded p-2 mb-3 text-xs space-y-1">
            {stopLoss && <p className="text-slate-400">Stop: <span className="text-white">€{(priceVal * (1 - parseFloat(stopLoss) / 100)).toFixed(2)}</span></p>}
            {takeProfit && <p className="text-slate-400">Target: <span className="text-white">€{(priceVal * (1 + parseFloat(takeProfit) / 100)).toFixed(2)}</span></p>}
            {quantity && <p className="text-slate-400">Total: <span className={totalAmount > 0 ? 'text-green-400' : 'text-slate-400'}>€{totalAmount.toFixed(2)}</span></p>}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-sm font-medium transition"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className={`flex-1 px-3 py-2 rounded text-sm font-medium transition text-white ${
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

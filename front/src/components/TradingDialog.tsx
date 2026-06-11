import { useState, useEffect } from 'react'
import { formatCurrency } from '@/utils/currency'
import { api } from '@/services/api'

interface TradingDialogProps {
  isOpen: boolean
  mode: 'buy' | 'sell'
  ticker: string
  position?: any
  currentPrice?: number
  portfolioName?: string
  onClose: () => void
  onConfirm: (quantity: number, price?: number, fees?: number, stopLoss?: number, takeProfit?: number) => void
}

export function TradingDialog({
  isOpen,
  mode,
  ticker: initialTicker,
  position,
  currentPrice: initialPrice = 0,
  portfolioName,
  onClose,
  onConfirm,
}: TradingDialogProps) {
  const [ticker, setTicker] = useState(initialTicker || '')
  const [tickerName, setTickerName] = useState('')
  const [price, setPrice] = useState<string>(initialPrice ? parseFloat(initialPrice).toFixed(3) : '')
  const [quantity, setQuantity] = useState<string>(
    mode === 'sell' && position?.quantity ? String(position.quantity) : mode === 'buy' ? '1' : ''
  )
  const [fees, setFees] = useState<string>('0')
  const [stopLoss, setStopLoss] = useState<string>('7') // Default 7%
  const [takeProfit, setTakeProfit] = useState<string>('2') // Default 2%
  const [createTodo, setCreateTodo] = useState(false)
  const [loadingTicker, setLoadingTicker] = useState(false)

  // Fetch ticker name when ticker changes
  useEffect(() => {
    if (!ticker) return

    // Try to get from position first
    if (position?.company_name) {
      setTickerName(position.company_name)
      return
    }

    // Otherwise fetch from API
    if (ticker) {
      fetchTickerName(ticker)
    }
  }, [ticker, position?.company_name])

  const fetchTickerName = async (tickerSymbol: string) => {
    try {
      setLoadingTicker(true)
      const response = await api.getTickerInfo?.(tickerSymbol)
      if (response?.name) {
        setTickerName(response.name)
      } else {
        // If API doesn't return name, try searching in watchlist
        console.log(`[TradingDialog] No name found for ${tickerSymbol}`)
      }
    } catch (err) {
      console.error('Failed to fetch ticker info:', err)
    } finally {
      setLoadingTicker(false)
    }
  }

  // Initialize ticker on dialog open
  useEffect(() => {
    if (isOpen && initialTicker && !ticker) {
      setTicker(initialTicker)
    }
  }, [isOpen, initialTicker])

  // Pre-fill form when opening dialog for sell
  useEffect(() => {
    if (isOpen && mode === 'sell' && position) {
      // Pre-fill quantity
      if (position.quantity) {
        setQuantity(String(position.quantity))
      }
      // Pre-fill price with current close price (latest) - max 3 decimal places
      const currentClosePrice = position.close || position.current_price || position.price || 0
      if (currentClosePrice) {
        setPrice(String(parseFloat(currentClosePrice).toFixed(3)))
      }
      // Pre-fill stop loss and take profit for sell
      setStopLoss('5') // 5% stop loss for sell
      setTakeProfit('3') // 3% take profit for sell
    }
  }, [isOpen, mode, position])

  // Reset form when dialog closes
  useEffect(() => {
    if (!isOpen) {
      resetForm()
    }
  }, [isOpen])

  const handleConfirm = async () => {
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

    if (createTodo) {
      // Create a task instead of executing the trade
      await createTodoTask(qty, priceVal, feesVal, stopVal, targetVal)
    } else {
      // Execute the trade normally
      onConfirm(qty, priceVal, feesVal, stopVal, targetVal)
    }
    resetForm()
  }

  const createTodoTask = async (qty: number, priceVal: number, feesVal: number, stopVal: number, targetVal: number) => {
    try {
      const modeText = mode.toUpperCase()
      const title = `${modeText} ${ticker} ${tickerName}`

      // Calculate summary values
      const total = priceVal * qty
      const stopAmount = total * (1 - stopVal)
      const targetAmount = total * (1 + targetVal)

      // Format description
      let description = `📊 Trade Details\n\n`
      if (portfolioName) {
        description += `Portfolio: ${portfolioName}\n`
      }
      description += `Type: ${modeText}\n`
      description += `Ticker: ${ticker}\n`
      description += `Company: ${tickerName}\n\n`

      description += `💰 Order Details\n\n`
      description += `Price: €${priceVal.toFixed(3)}\n`
      description += `Quantity: ${qty.toFixed(2)} shares\n`
      description += `Fees: €${feesVal.toFixed(2)}\n\n`

      description += `📈 Calculations\n\n`
      description += `Total: €${total.toFixed(2)}\n`

      if (mode === 'buy') {
        description += `Stop Loss: €${stopAmount.toFixed(2)} (${(stopVal * 100).toFixed(1)}%)\n`
        description += `Take Profit: €${targetAmount.toFixed(2)} (${(targetVal * 100).toFixed(1)}%)\n`
      } else if (position?.avg_entry_price) {
        const profit = (priceVal - position.avg_entry_price) * qty
        const gainPct = ((priceVal - position.avg_entry_price) / position.avg_entry_price) * 100
        description += `Entry Price: €${position.avg_entry_price.toFixed(3)}\n`
        description += `Profit: €${profit.toFixed(2)}\n`
        description += `Gain %: ${gainPct.toFixed(2)}%\n`
      }

      const today = new Date().toISOString().split('T')[0]

      const response = await fetch('http://192.168.0.130:6501/api/v1/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          description,
          priority: 'High',
          due_date: today,
          status: 'To-Do',
          tags: ['trading', mode],
        }),
      })

      if (!response.ok) throw new Error('Failed to create task')

      alert(`Task created: ${title}`)
      onClose()
    } catch (err) {
      console.error('Failed to create task:', err)
      alert('Failed to create task')
    }
  }

  const resetForm = () => {
    setTicker(initialTicker || '')
    setPrice(initialPrice ? parseFloat(initialPrice).toFixed(3) : '')
    setQuantity('')
    setFees('0')
    setStopLoss('7')
    setTakeProfit('2')
    setCreateTodo(false)
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
          <div>
            <h2 className="text-lg font-bold text-white">
              {mode === 'buy' ? '📈' : '📉'} {ticker || '...'}
            </h2>
            {tickerName && <p className="text-xs text-slate-400">{tickerName}</p>}
            {portfolioName && <p className="text-xs text-slate-500 mt-1">Portfolio: {portfolioName}</p>}
          </div>
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

          <div className={`grid gap-2 ${mode === 'sell' ? 'grid-cols-1' : 'grid-cols-3'}`}>
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
            {mode === 'buy' && (
              <>
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
              </>
            )}
          </div>
        </div>

        {/* Calculations */}
        {priceVal > 0 && quantity && (
          <div className="bg-slate-800/30 rounded p-2 mb-3 text-xs space-y-1">
            <p className="text-slate-400">Total: <span className={totalAmount > 0 ? 'text-white font-bold' : 'text-slate-400'}>€{totalAmount.toFixed(2)}</span></p>
            {mode === 'sell' && position?.avg_entry_price && (
              <>
                {(() => {
                  const entryPrice = parseFloat(position.avg_entry_price)
                  const profit = (priceVal - entryPrice) * qtyVal - feesVal
                  const gainPct = ((priceVal - entryPrice) / entryPrice) * 100
                  return (
                    <>
                      <p className="text-slate-400">Profit: <span className={profit >= 0 ? 'text-green-400 font-medium' : 'text-red-400 font-medium'}>€{profit.toFixed(2)}</span></p>
                      <p className="text-slate-400">Gain %: <span className={gainPct >= 0 ? 'text-green-400 font-medium' : 'text-red-400 font-medium'}>{gainPct.toFixed(2)}%</span></p>
                    </>
                  )
                })()}
              </>
            )}
            {mode === 'buy' && (
              <>
                {stopLoss && <p className="text-slate-400">Stop: <span className="text-white">€{(priceVal * (1 - parseFloat(stopLoss) / 100)).toFixed(2)}</span></p>}
                {takeProfit && <p className="text-slate-400">Target: <span className="text-white">€{(priceVal * (1 + parseFloat(takeProfit) / 100)).toFixed(2)}</span></p>}
              </>
            )}
          </div>
        )}

        {/* Summary */}
        <div className="bg-slate-800 rounded-lg p-3 mb-3 border border-slate-700">
          {mode === 'buy' ? (
            <>
              <div className="flex justify-between mb-2">
                <span className="text-slate-400">Total:</span>
                <span className="text-white font-semibold">€{(priceVal * qtyVal).toFixed(2)}</span>
              </div>
              <div className="flex justify-between mb-2">
                <span className="text-slate-400">Stop:</span>
                <span className="text-red-400 font-semibold">€{(priceVal * qtyVal * (1 - parseFloat(stopLoss || '0') / 100)).toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Target:</span>
                <span className="text-green-400 font-semibold">€{(priceVal * qtyVal * (1 + parseFloat(takeProfit || '0') / 100)).toFixed(2)}</span>
              </div>
            </>
          ) : (
            <>
              <div className="flex justify-between mb-2">
                <span className="text-slate-400">Total:</span>
                <span className="text-white font-semibold">€{(priceVal * qtyVal).toFixed(2)}</span>
              </div>
              {position?.avg_entry_price && (
                <>
                  <div className="flex justify-between mb-2">
                    <span className="text-slate-400">Profit:</span>
                    <span className={`font-semibold ${(priceVal - position.avg_entry_price) * qtyVal >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      €{((priceVal - position.avg_entry_price) * qtyVal).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Gain %:</span>
                    <span className={`font-semibold ${(priceVal - position.avg_entry_price) / position.avg_entry_price >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {(((priceVal - position.avg_entry_price) / position.avg_entry_price) * 100).toFixed(2)}%
                    </span>
                  </div>
                </>
              )}
            </>
          )}
        </div>

        {/* Todo Checkbox */}
        <div className="flex items-center gap-2 mb-3">
          <input
            type="checkbox"
            id="create-todo"
            checked={createTodo}
            onChange={(e) => setCreateTodo(e.target.checked)}
            className="w-4 h-4 rounded border-slate-600 cursor-pointer"
          />
          <label htmlFor="create-todo" className="text-sm text-slate-300 cursor-pointer">
            Create task instead of trading
          </label>
        </div>

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
            {createTodo ? 'Create Task' : (mode === 'buy' ? 'Buy' : 'Sell')}
          </button>
        </div>
      </div>
    </div>
  )
}

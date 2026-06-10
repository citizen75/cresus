import { useState, useEffect } from 'react'
import { formatCurrency } from '@/utils/currency'
import { api } from '@/services/api'

interface TradingWidgetProps {
  onOrderPlaced?: (order: any) => void
}

export function TradingWidget({ onOrderPlaced }: TradingWidgetProps) {
  const [mode, setMode] = useState<'buy' | 'sell'>('buy')
  const [ticker, setTicker] = useState('')
  const [tickerName, setTickerName] = useState('')
  const [price, setPrice] = useState<string>('')
  const [quantity, setQuantity] = useState<string>('')
  const [fees, setFees] = useState<string>('0')
  const [stopLoss, setStopLoss] = useState<string>('7')
  const [takeProfit, setTakeProfit] = useState<string>('2')
  const [loadingTicker, setLoadingTicker] = useState(false)
  const [recentOrders, setRecentOrders] = useState<any[]>([])

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

  useEffect(() => {
    if (ticker && ticker.length > 0) {
      fetchTickerName(ticker)
    } else {
      setTickerName('')
    }
  }, [ticker])

  const handlePlaceOrder = () => {
    if (!ticker) {
      alert('Please enter a ticker')
      return
    }

    const qty = parseFloat(quantity)
    if (isNaN(qty) || qty <= 0) {
      alert('Please enter a valid quantity')
      return
    }

    const priceVal = parseFloat(price)
    if (isNaN(priceVal) || priceVal <= 0) {
      alert('Please enter a valid price')
      return
    }

    const feesVal = parseFloat(fees || '0')
    const stopVal = parseFloat(stopLoss || '0')
    const targetVal = parseFloat(takeProfit || '0')
    const totalAmount = qty * priceVal - feesVal

    const order = {
      id: Date.now(),
      mode,
      ticker,
      name: tickerName,
      price: priceVal,
      quantity: qty,
      fees: feesVal,
      stopLoss: stopVal,
      takeProfit: targetVal,
      total: totalAmount,
      timestamp: new Date().toLocaleString(),
    }

    // Add to recent orders
    setRecentOrders([order, ...recentOrders.slice(0, 4)])

    // Call callback
    onOrderPlaced?.(order)

    // Show confirmation
    alert(`${mode.toUpperCase()} order placed:\n${qty} × ${ticker} @ €${priceVal.toFixed(2)}`)

    // Reset form
    resetForm()
  }

  const resetForm = () => {
    setTicker('')
    setTickerName('')
    setPrice('')
    setQuantity('')
    setFees('0')
    setStopLoss('7')
    setTakeProfit('2')
  }

  const priceVal = parseFloat(price || '0') || 0
  const qtyVal = parseFloat(quantity || '0') || 0
  const feesVal = parseFloat(fees || '0') || 0
  const totalAmount = qtyVal * priceVal - feesVal

  return (
    <div className="flex flex-col h-full bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-slate-800 bg-slate-800/50 px-4 py-3">
        <h3 className="text-lg font-bold text-white mb-3">Quick Trading</h3>

        {/* Mode Toggle */}
        <div className="flex gap-2">
          <button
            onClick={() => setMode('buy')}
            className={`flex-1 px-3 py-2 rounded text-sm font-medium transition ${
              mode === 'buy'
                ? 'bg-green-600 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            💰 Buy
          </button>
          <button
            onClick={() => setMode('sell')}
            className={`flex-1 px-3 py-2 rounded text-sm font-medium transition ${
              mode === 'sell'
                ? 'bg-red-600 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            📊 Sell
          </button>
        </div>
      </div>

      {/* Form */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {/* Ticker */}
        <div>
          <label className="block text-xs text-slate-400 mb-1">Ticker</label>
          <input
            type="text"
            placeholder="e.g., AAPL"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white text-sm rounded focus:outline-none focus:border-purple-600"
          />
          {tickerName && <p className="text-xs text-slate-400 mt-1">📊 {tickerName}</p>}
          {loadingTicker && <p className="text-xs text-slate-500 mt-1">Loading...</p>}
        </div>

        {/* Price & Qty Row */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Price</label>
            <input
              type="number"
              step="0.01"
              placeholder="0.00"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white text-sm rounded focus:outline-none focus:border-purple-600"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Qty</label>
            <input
              type="number"
              step="0.01"
              placeholder="0.00"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white text-sm rounded focus:outline-none focus:border-purple-600"
            />
          </div>
        </div>

        {/* Fees & Risk Row */}
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Fees</label>
            <input
              type="number"
              step="0.01"
              placeholder="0"
              value={fees}
              onChange={(e) => setFees(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white text-sm rounded focus:outline-none focus:border-purple-600"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Stop %</label>
            <input
              type="number"
              step="0.1"
              placeholder="7"
              value={stopLoss}
              onChange={(e) => setStopLoss(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white text-sm rounded focus:outline-none focus:border-purple-600"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Target %</label>
            <input
              type="number"
              step="0.1"
              placeholder="2"
              value={takeProfit}
              onChange={(e) => setTakeProfit(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white text-sm rounded focus:outline-none focus:border-purple-600"
            />
          </div>
        </div>

        {/* Calculations */}
        {priceVal > 0 && (
          <div className="bg-slate-800/50 rounded p-3 space-y-1 text-xs">
            {stopLoss && <p className="text-slate-400">Stop: <span className="text-white font-medium">€{(priceVal * (1 - parseFloat(stopLoss) / 100)).toFixed(2)}</span></p>}
            {takeProfit && <p className="text-slate-400">Target: <span className="text-white font-medium">€{(priceVal * (1 + parseFloat(takeProfit) / 100)).toFixed(2)}</span></p>}
            {quantity && (
              <p className="text-slate-400">Total: <span className={totalAmount > 0 ? 'text-green-400 font-medium' : 'text-slate-500'}>
                €{totalAmount.toFixed(2)}
              </span></p>
            )}
          </div>
        )}

        {/* Place Order Button */}
        <button
          onClick={handlePlaceOrder}
          className={`w-full px-4 py-2 rounded font-medium transition text-white ${
            mode === 'buy'
              ? 'bg-green-600 hover:bg-green-700'
              : 'bg-red-600 hover:bg-red-700'
          }`}
        >
          {mode === 'buy' ? '💰 Place Buy Order' : '📊 Place Sell Order'}
        </button>
      </div>

      {/* Recent Orders */}
      {recentOrders.length > 0 && (
        <div className="flex-shrink-0 border-t border-slate-800 bg-slate-800/30 p-3 max-h-40 overflow-y-auto">
          <p className="text-xs text-slate-400 mb-2 font-medium">Recent Orders</p>
          <div className="space-y-2">
            {recentOrders.map((order) => (
              <div key={order.id} className="bg-slate-800/50 rounded p-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-white">{order.ticker}</span>
                  <span className={`px-2 py-0.5 rounded ${
                    order.mode === 'buy'
                      ? 'bg-green-900/30 text-green-300'
                      : 'bg-red-900/30 text-red-300'
                  }`}>
                    {order.mode.toUpperCase()}
                  </span>
                </div>
                <div className="text-slate-400 mt-1">
                  {order.quantity} @ €{order.price.toFixed(2)} = €{order.total.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

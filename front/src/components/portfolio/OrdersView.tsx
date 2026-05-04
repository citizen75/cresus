import { useState, useEffect } from 'react'
import CardChart from '@/components/CardChart'
import Spinner from '@/components/Spinner'

interface OrdersViewProps {
  name: string
}

interface Order {
  id: string
  ticker: string
  shares: number
  entryPrice: number
  executionMethod: string
  stopLoss?: number
  takeProfit?: number
  riskAmount?: number
  riskReward?: number
  status: string
  filledQuantity?: number
  filledPrice?: number
  executedAt?: string
  reason?: string
}

interface HistoricalData {
  [ticker: string]: Array<{ date: string; close: number; ema_20?: number; ema_50?: number }>
}

export default function OrdersView({ name }: OrdersViewProps) {
  const [orders, setOrders] = useState<Order[]>([])
  const [historicalData, setHistoricalData] = useState<HistoricalData>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table')
  const [statusFilter, setStatusFilter] = useState('All')
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState('Risk/Reward')
  const [currentPage, setCurrentPage] = useState(1)
  const [period, setPeriod] = useState('1Y')

  const itemsPerPage = 10
  const totalPages = Math.ceil(orders.length / itemsPerPage)

  // Reload historical data when period changes
  useEffect(() => {
    if (orders.length > 0) {
      loadHistoricalData(orders.map(o => o.ticker), period)
    }
  }, [period])

  // Load orders from API
  useEffect(() => {
    const loadOrders = async () => {
      try {
        setLoading(true)
        const response = await fetch(`/api/portfolios/${encodeURIComponent(name)}/orders`)
        if (!response.ok) {
          setOrders([])
          setLoading(false)
          return
        }
        const data = await response.json()
        setOrders(data.orders || [])
        if (data.orders && data.orders.length > 0) {
          loadHistoricalData(
            data.orders.map((o: Order) => o.ticker),
            period
          )
        }
      } catch (err) {
        setError('Failed to load orders')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    loadOrders()
  }, [name])

  const loadHistoricalData = async (tickers: string[], period: string) => {
    try {
      const data: HistoricalData = {}
      for (const ticker of tickers) {
        try {
          const response = await fetch(
            `/api/data/history?ticker=${ticker}&days=${
              period === '1D' ? 1 : period === '1W' ? 7 : period === '1M' ? 30 : period === '3M' ? 90 : period === '6M' ? 180 : 365
            }`
          )
          if (response.ok) {
            const histData = await response.json()
            if (histData.history) {
              data[ticker] = histData.history.map((h: any) => ({
                date: h.timestamp || h.date,
                close: h.close,
                ema_20: h.ema_20,
                ema_50: h.ema_50,
              }))
            }
          }
        } catch (err) {
          console.error(`Failed to load history for ${ticker}:`, err)
        }
      }
      setHistoricalData(data)
    } catch (err) {
      console.error('Failed to load historical data:', err)
    }
  }

  // Filter and sort orders
  const filtered = orders
    .filter((order) => {
      const matchesStatus = statusFilter === 'All' || order.status.toLowerCase() === statusFilter.toLowerCase()
      const matchesSearch = order.ticker.toLowerCase().includes(searchTerm.toLowerCase())
      return matchesStatus && matchesSearch
    })
    .sort((a, b) => {
      if (sortBy === 'Risk/Reward') return (b.riskReward || 0) - (a.riskReward || 0)
      if (sortBy === 'Shares') return b.shares - a.shares
      if (sortBy === 'Entry Price') return b.entryPrice - a.entryPrice
      return 0
    })

  const paginatedItems = filtered.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)

  const getStatusColor = (status: string) => {
    if (status.toLowerCase() === 'filled') return 'bg-green-900/30 text-green-400'
    if (status.toLowerCase() === 'pending') return 'bg-yellow-900/30 text-yellow-400'
    return 'bg-slate-800/30 text-slate-400'
  }

  const getExecutionMethodColor = (method: string) => {
    if (method.toLowerCase() === 'market') return 'bg-blue-900/30 text-blue-400'
    if (method.toLowerCase() === 'limit') return 'bg-purple-900/30 text-purple-400'
    if (method.toLowerCase() === 'scale_in') return 'bg-cyan-900/30 text-cyan-400'
    return 'bg-slate-800/30 text-slate-400'
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-4 flex-wrap">
          <input
            type="text"
            placeholder="Search ticker..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              setCurrentPage(1)
            }}
            className="px-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:border-purple-600 outline-none transition"
          />

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value)
              setCurrentPage(1)
            }}
            className="px-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white focus:border-purple-600 outline-none transition"
          >
            <option>All</option>
            <option>Filled</option>
            <option>Pending</option>
            <option>Rejected</option>
          </select>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white focus:border-purple-600 outline-none transition"
          >
            <option>Risk/Reward</option>
            <option>Shares</option>
            <option>Entry Price</option>
          </select>

          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="px-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-white focus:border-purple-600 outline-none transition"
          >
            <option>1D</option>
            <option>1W</option>
            <option>1M</option>
            <option>3M</option>
            <option>6M</option>
            <option>1Y</option>
          </select>
        </div>

        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg p-1">
          <button
            onClick={() => {
              setViewMode('table')
              setCurrentPage(1)
            }}
            className={`px-4 py-2 rounded transition text-sm font-medium ${
              viewMode === 'table' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Table
          </button>
          <button
            onClick={() => {
              setViewMode('cards')
              setCurrentPage(1)
            }}
            className={`px-4 py-2 rounded transition text-sm font-medium ${
              viewMode === 'cards' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Cards
          </button>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Spinner />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="p-6 bg-red-900/20 border border-red-800 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {/* Empty State */}
      {!loading && orders.length === 0 && (
        <div className="text-center py-12 text-slate-400">
          No orders found for this portfolio
        </div>
      )}

      {/* Table View */}
      {!loading && viewMode === 'table' && orders.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-800/50 border-b border-slate-800">
                <tr>
                  <th className="px-6 py-4 text-left text-slate-400 font-medium">Ticker</th>
                  <th className="px-6 py-4 text-left text-slate-400 font-medium">Shares</th>
                  <th className="px-6 py-4 text-left text-slate-400 font-medium">Entry Price</th>
                  <th className="px-6 py-4 text-left text-slate-400 font-medium">Execution</th>
                  <th className="px-6 py-4 text-left text-slate-400 font-medium">Stop Loss</th>
                  <th className="px-6 py-4 text-left text-slate-400 font-medium">Take Profit</th>
                  <th className="px-6 py-4 text-left text-slate-400 font-medium">R/R</th>
                  <th className="px-6 py-4 text-left text-slate-400 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {paginatedItems.map((order) => (
                  <tr key={order.id} className="border-t border-slate-800 hover:bg-slate-800/30 transition">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 bg-slate-700 rounded flex items-center justify-center text-xs font-bold text-white">
                          {order.ticker.charAt(0)}
                        </div>
                        <span className="text-white font-medium">{order.ticker}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-white">{order.shares}</td>
                    <td className="px-6 py-4 text-white font-medium">€{order.entryPrice.toFixed(2)}</td>
                    <td className="px-6 py-4">
                      <span className={`px-3 py-1 rounded text-xs font-medium ${getExecutionMethodColor(order.executionMethod)}`}>
                        {order.executionMethod.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-white">{order.stopLoss ? `€${order.stopLoss.toFixed(2)}` : '—'}</td>
                    <td className="px-6 py-4 text-white">{order.takeProfit ? `€${order.takeProfit.toFixed(2)}` : '—'}</td>
                    <td className="px-6 py-4">
                      {order.riskReward ? (
                        <span className="text-white font-medium">{order.riskReward.toFixed(2)}x</span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-3 py-1 rounded text-xs font-medium ${getStatusColor(order.status)}`}>
                        {order.status.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="px-6 py-4 border-t border-slate-800 bg-slate-900 flex items-center justify-between">
            <p className="text-slate-400 text-sm">Showing 1-{Math.min(itemsPerPage, filtered.length)} of {filtered.length}</p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 bg-slate-800 border border-slate-700 text-slate-300 rounded hover:bg-slate-700 disabled:opacity-50 transition"
              >
                ←
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                <button
                  key={page}
                  onClick={() => setCurrentPage(page)}
                  className={`px-3 py-1 rounded transition ${
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
                className="px-3 py-1 bg-slate-800 border border-slate-700 text-slate-300 rounded hover:bg-slate-700 disabled:opacity-50 transition"
              >
                →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cards View */}
      {!loading && viewMode === 'cards' && orders.length > 0 && (
        <div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {paginatedItems.map((order) => (
              <div key={order.id} className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden hover:border-purple-600/50 transition">
                {/* Card Header */}
                <div className="bg-slate-800/50 border-b border-slate-800 p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="text-white font-bold text-lg">{order.ticker}</p>
                      <p className="text-slate-400 text-xs">{order.shares} shares</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-purple-400">{order.riskReward?.toFixed(2) || '—'}x</p>
                      <p className="text-slate-400 text-xs">Risk/Reward</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getExecutionMethodColor(order.executionMethod)}`}>
                      {order.executionMethod.toUpperCase()}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(order.status)}`}>
                      {order.status.toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Chart */}
                {historicalData[order.ticker] && historicalData[order.ticker].length > 0 ? (
                  <CardChart data={historicalData[order.ticker]} ticker={order.ticker} />
                ) : (
                  <div className="p-4 h-48 bg-slate-800/20 flex items-center justify-center">
                    <Spinner />
                  </div>
                )}

                {/* Card Footer */}
                <div className="border-t border-slate-800 p-4 space-y-3">
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <p className="text-slate-500 mb-1">Entry</p>
                      <p className="text-white font-medium">€{order.entryPrice.toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 mb-1">Stop Loss</p>
                      <p className="text-red-400 font-medium">{order.stopLoss ? `€${order.stopLoss.toFixed(2)}` : '—'}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 mb-1">Target</p>
                      <p className="text-green-400 font-medium">{order.takeProfit ? `€${order.takeProfit.toFixed(2)}` : '—'}</p>
                    </div>
                  </div>
                  {order.reason && (
                    <div className="text-xs pt-2 border-t border-slate-700">
                      <p className="text-slate-500 mb-1">Note:</p>
                      <p className="text-slate-300">{order.reason}</p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Cards Pagination */}
          <div className="mt-4 flex items-center justify-center gap-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 bg-slate-800 border border-slate-700 text-slate-300 rounded hover:bg-slate-700 disabled:opacity-50 transition"
            >
              ←
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
                className={`px-3 py-1 rounded transition ${
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
              className="px-3 py-1 bg-slate-800 border border-slate-700 text-slate-300 rounded hover:bg-slate-700 disabled:opacity-50 transition"
            >
              →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

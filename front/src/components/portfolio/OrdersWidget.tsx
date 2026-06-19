import { useState } from 'react'
import { formatCurrency } from '@/utils/currency'

interface Order {
  id: string
  ticker: string
  operation?: string
  shares: number
  entryPrice: number
  executionMethod: string
  stopLoss?: number
  takeProfit?: number
  riskAmount?: number
  riskReward?: number
  status: string
  createdAt: string
  metadata?: Record<string, any>
}

interface OrdersWidgetProps {
  orders: Order[]
  isLoading?: boolean
  currency?: string
}

const TABS = [
  { id: 'activity', label: 'Activity' },
  { id: 'orders', label: 'Orders' },
  { id: 'trades', label: 'Trades' },
] as const

type TabId = (typeof TABS)[number]['id']

function getStatusColor(status: string) {
  const s = status.toLowerCase()
  if (s === 'executed' || s === 'filled') return 'bg-green-900/30 text-green-400'
  if (s === 'pending') return 'bg-yellow-900/30 text-yellow-400'
  if (s === 'rejected') return 'bg-red-900/30 text-red-400'
  if (s === 'expired' || s === 'cancelled') return 'bg-slate-700/40 text-slate-400'
  return 'bg-slate-800/30 text-slate-400'
}

export default function OrdersWidget({ orders, isLoading = false, currency = 'USD' }: OrdersWidgetProps) {
  const [activeTab, setActiveTab] = useState<TabId>('activity')

  const filtered = orders.filter((order) => {
    if (activeTab === 'orders') return order.status.toUpperCase() === 'PENDING'
    if (activeTab === 'trades') return order.status.toUpperCase() === 'EXECUTED'
    return true
  })

  const pendingCount = orders.filter((o) => o.status.toUpperCase() === 'PENDING').length
  const tradesCount = orders.filter((o) => o.status.toUpperCase() === 'EXECUTED').length

  const countFor = (id: TabId) => {
    if (id === 'orders') return pendingCount
    if (id === 'trades') return tradesCount
    return orders.length
  }

  return (
    <div className="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
      <div className="border-b border-slate-800 flex-shrink-0">
        <div className="flex gap-6 px-4">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-1 py-3 font-medium text-sm transition border-b-2 whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-purple-600 text-white'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              {tab.label} ({countFor(tab.id)})
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="text-center py-8 text-slate-400 text-sm">Loading orders...</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">No {activeTab} to show</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-800/50 border-b border-slate-800 sticky top-0">
              <tr>
                <th className="px-4 py-2 text-left text-slate-400 font-medium">Date</th>
                <th className="px-4 py-2 text-left text-slate-400 font-medium">Ticker</th>
                <th className="px-4 py-2 text-left text-slate-400 font-medium">Side</th>
                <th className="px-4 py-2 text-right text-slate-400 font-medium">Shares</th>
                <th className="px-4 py-2 text-right text-slate-400 font-medium">Price</th>
                <th className="px-4 py-2 text-right text-slate-400 font-medium">Stop</th>
                <th className="px-4 py-2 text-right text-slate-400 font-medium">Target</th>
                <th className="px-4 py-2 text-right text-slate-400 font-medium">R/R</th>
                <th className="px-4 py-2 text-left text-slate-400 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {filtered.map((order) => (
                <tr key={order.id} className="hover:bg-slate-800/30 transition">
                  <td className="px-4 py-2 text-slate-400">{(order.createdAt || '').slice(0, 10)}</td>
                  <td className="px-4 py-2 text-white font-medium">{order.ticker}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      order.operation === 'SELL' ? 'bg-red-900/30 text-red-300' : 'bg-blue-900/30 text-blue-300'
                    }`}>
                      {order.operation || '-'}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right text-slate-300">{order.shares}</td>
                  <td className="px-4 py-2 text-right text-slate-300">{formatCurrency(order.entryPrice, currency)}</td>
                  <td className="px-4 py-2 text-right text-slate-300">{order.stopLoss ? formatCurrency(order.stopLoss, currency) : '—'}</td>
                  <td className="px-4 py-2 text-right text-slate-300">{order.takeProfit ? formatCurrency(order.takeProfit, currency) : '—'}</td>
                  <td className="px-4 py-2 text-right text-slate-300">{order.riskReward ? `${order.riskReward.toFixed(2)}x` : '—'}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(order.status)}`}>
                      {order.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

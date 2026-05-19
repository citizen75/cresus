import { useState } from 'react'
import { api } from '@/services/api'

interface Alert {
  id: string
  type: 'price' | 'performance' | 'portfolio' | 'system'
  title: string
  message: string
  severity: 'info' | 'warning' | 'critical'
  triggered_at?: string
  read: boolean
}

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([
    {
      id: '1',
      type: 'price',
      title: 'Price Alert',
      message: 'AAPL exceeded target price of $250',
      severity: 'info',
      triggered_at: new Date().toISOString(),
      read: false,
    },
    {
      id: '2',
      type: 'performance',
      title: 'Performance Warning',
      message: 'Portfolio drawdown exceeds 10% threshold',
      severity: 'warning',
      triggered_at: new Date(Date.now() - 3600000).toISOString(),
      read: false,
    },
    {
      id: '3',
      type: 'portfolio',
      title: 'Portfolio Update',
      message: 'New position opened in tech sector',
      severity: 'info',
      triggered_at: new Date(Date.now() - 86400000).toISOString(),
      read: true,
    },
  ])

  const [filterType, setFilterType] = useState<'all' | Alert['type']>('all')
  const [showUnreadOnly, setShowUnreadOnly] = useState(false)

  const filteredAlerts = alerts.filter((alert) => {
    if (filterType !== 'all' && alert.type !== filterType) return false
    if (showUnreadOnly && alert.read) return false
    return true
  })

  const unreadCount = alerts.filter((a) => !a.read).length

  const markAsRead = (id: string) => {
    setAlerts(alerts.map((a) => (a.id === id ? { ...a, read: true } : a)))
  }

  const markAllAsRead = () => {
    setAlerts(alerts.map((a) => ({ ...a, read: true })))
  }

  const deleteAlert = (id: string) => {
    setAlerts(alerts.filter((a) => a.id !== id))
  }

  const getSeverityColor = (severity: Alert['severity']) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-900/30 border-red-800 text-red-400'
      case 'warning':
        return 'bg-yellow-900/30 border-yellow-800 text-yellow-400'
      case 'info':
        return 'bg-blue-900/30 border-blue-800 text-blue-400'
      default:
        return 'bg-slate-800/30 border-slate-800 text-slate-400'
    }
  }

  const getSeverityIcon = (severity: Alert['severity']) => {
    switch (severity) {
      case 'critical':
        return '🔴'
      case 'warning':
        return '🟡'
      case 'info':
        return '🔵'
      default:
        return '⚪'
    }
  }

  const getTypeLabel = (type: Alert['type']) => {
    switch (type) {
      case 'price':
        return '💰 Price'
      case 'performance':
        return '📈 Performance'
      case 'portfolio':
        return '💼 Portfolio'
      case 'system':
        return '⚙️ System'
      default:
        return type
    }
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return ''
    const date = new Date(dateString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (hours < 1) return 'Just now'
    if (hours < 24) return `${hours}h ago`
    if (days < 7) return `${days}d ago`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">Alerts</h1>
          <p className="text-slate-400">Manage your portfolio and market alerts</p>
        </div>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <div className="px-3 py-1 bg-red-900/30 border border-red-800 rounded text-red-400 text-sm font-medium">
              {unreadCount} unread
            </div>
          )}
          {unreadCount > 0 && (
            <button
              onClick={markAllAsRead}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-medium transition text-sm"
            >
              Mark all as read
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2 bg-slate-800/30 border border-slate-700 rounded-lg p-1 w-fit">
          <button
            onClick={() => setFilterType('all')}
            className={`px-3 py-2 rounded transition font-medium text-sm ${
              filterType === 'all'
                ? 'bg-purple-600 text-white'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilterType('price')}
            className={`px-3 py-2 rounded transition font-medium text-sm ${
              filterType === 'price'
                ? 'bg-purple-600 text-white'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            💰 Price
          </button>
          <button
            onClick={() => setFilterType('performance')}
            className={`px-3 py-2 rounded transition font-medium text-sm ${
              filterType === 'performance'
                ? 'bg-purple-600 text-white'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            📈 Performance
          </button>
          <button
            onClick={() => setFilterType('portfolio')}
            className={`px-3 py-2 rounded transition font-medium text-sm ${
              filterType === 'portfolio'
                ? 'bg-purple-600 text-white'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            💼 Portfolio
          </button>
          <button
            onClick={() => setFilterType('system')}
            className={`px-3 py-2 rounded transition font-medium text-sm ${
              filterType === 'system'
                ? 'bg-purple-600 text-white'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            ⚙️ System
          </button>
        </div>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showUnreadOnly}
            onChange={(e) => setShowUnreadOnly(e.target.checked)}
            className="rounded border-slate-600"
          />
          <span className="text-sm text-slate-400">Unread only</span>
        </label>
      </div>

      {/* Alerts List */}
      <div className="space-y-3">
        {filteredAlerts.length === 0 ? (
          <div className="bg-slate-900/50 rounded-lg p-12 border border-slate-800 text-center">
            <p className="text-slate-400 text-lg mb-2">
              {showUnreadOnly && unreadCount === 0 ? 'No unread alerts' : 'No alerts'}
            </p>
            <p className="text-slate-500 text-sm">
              {showUnreadOnly
                ? 'All alerts have been read'
                : 'You will receive alerts about prices, performance, and portfolio changes'}
            </p>
          </div>
        ) : (
          filteredAlerts.map((alert) => (
            <div
              key={alert.id}
              className={`border rounded-lg p-4 transition ${
                alert.read
                  ? 'bg-slate-900/30 border-slate-800'
                  : 'bg-slate-900/50 border-purple-600/50'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-4 flex-1">
                  {/* Icon */}
                  <div className={`pt-1 text-xl ${getSeverityIcon(alert.severity)}`} />

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className={`text-sm font-bold ${
                        alert.read ? 'text-slate-400' : 'text-white'
                      }`}>
                        {alert.title}
                      </h3>
                      <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-400">
                        {getTypeLabel(alert.type)}
                      </span>
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${getSeverityColor(
                        alert.severity
                      )}`}>
                        {alert.severity}
                      </span>
                    </div>
                    <p className={`text-sm ${
                      alert.read ? 'text-slate-500' : 'text-slate-300'
                    }`}>
                      {alert.message}
                    </p>
                    <p className="text-xs text-slate-500 mt-2">
                      {formatDate(alert.triggered_at)}
                    </p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  {!alert.read && (
                    <button
                      onClick={() => markAsRead(alert.id)}
                      className="px-2 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition"
                      title="Mark as read"
                    >
                      ✓
                    </button>
                  )}
                  <button
                    onClick={() => deleteAlert(alert.id)}
                    className="px-2 py-1 text-xs bg-slate-800 hover:bg-red-900/20 text-slate-300 hover:text-red-400 rounded transition"
                    title="Delete alert"
                  >
                    ✕
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Stats */}
      {alerts.length > 0 && (
        <div className="grid grid-cols-4 gap-3">
          <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-800">
            <div className="text-slate-400 text-xs mb-1">Total Alerts</div>
            <div className="text-2xl font-bold text-white">{alerts.length}</div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-800">
            <div className="text-slate-400 text-xs mb-1">Unread</div>
            <div className={`text-2xl font-bold ${unreadCount > 0 ? 'text-red-400' : 'text-slate-400'}`}>
              {unreadCount}
            </div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-800">
            <div className="text-slate-400 text-xs mb-1">Critical</div>
            <div className="text-2xl font-bold text-red-400">
              {alerts.filter((a) => a.severity === 'critical').length}
            </div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-800">
            <div className="text-slate-400 text-xs mb-1">Warnings</div>
            <div className="text-2xl font-bold text-yellow-400">
              {alerts.filter((a) => a.severity === 'warning').length}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

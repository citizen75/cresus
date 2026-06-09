import { useState, useEffect, useRef, useCallback, Suspense } from 'react'
import { AlertMessageRenderer } from './AlertMessageRenderer'

interface MessageWidget {
  type: 'portfolio_holdings' | 'portfolio_positions' | 'market_overview' | 'trade_analysis'
  data: Record<string, any>
}

interface ConversationMessage {
  id?: string
  type?: 'alert' | 'signal' | 'portfolio' | 'llm' | 'user'
  source: string
  content: string
  datetime: string
  portfolio?: string
  signal?: string
  tickers?: string[]
  widget?: MessageWidget
}

interface ConversationWidgetProps {
  portfolioName: string
  sourceFilter?: string
  title?: string
  subtitle?: string
  showRefreshButton?: boolean
  onRefresh?: () => void
  maxHeight?: string
  onSendMessage?: (message: string) => Promise<void>
}

// Dynamic widget loader
const WidgetRenderer = ({ widget }: { widget: MessageWidget }) => {
  if (!widget) return null

  switch (widget.type) {
    case 'portfolio_holdings':
      return (
        <div className="mt-2 bg-slate-700/30 rounded p-2 border border-slate-600">
          <div className="text-xs font-semibold text-slate-300 mb-2">Holdings:</div>
          <div className="space-y-1">
            {widget.data?.holdings?.map((holding: any, i: number) => (
              <div key={i} className="text-xs text-slate-400 flex justify-between">
                <span>{holding.ticker}</span>
                <span className="text-slate-500">{holding.shares} @ ${holding.price}</span>
              </div>
            ))}
          </div>
        </div>
      )

    case 'portfolio_positions':
      return (
        <div className="mt-2 bg-slate-700/30 rounded p-2 border border-slate-600">
          <div className="text-xs font-semibold text-slate-300 mb-2">Positions:</div>
          <div className="space-y-1">
            {widget.data?.positions?.map((pos: any, i: number) => (
              <div key={i} className="text-xs text-slate-400 flex justify-between">
                <span>{pos.ticker}</span>
                <span className={pos.pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                  {pos.pnl >= 0 ? '+' : ''}{pos.pnl}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )

    case 'trade_analysis':
      return (
        <div className="mt-2 bg-slate-700/30 rounded p-2 border border-slate-600">
          <div className="text-xs font-semibold text-slate-300 mb-2">Analysis:</div>
          <div className="text-xs text-slate-400 space-y-1">
            <div>Entry: ${widget.data?.entry_price}</div>
            <div>Target: ${widget.data?.target_price}</div>
            <div>Stop: ${widget.data?.stop_loss}</div>
            <div className="text-slate-500">R/R: {widget.data?.rr_ratio?.toFixed(2)}</div>
          </div>
        </div>
      )

    default:
      return null
  }
}

export function ConversationWidget({
  portfolioName,
  sourceFilter,
  title = 'Global Chat',
  subtitle,
  showRefreshButton = true,
  onRefresh,
  maxHeight = 'h-96',
  onSendMessage
}: ConversationWidgetProps) {
  const [messages, setMessages] = useState<ConversationMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [inputValue, setInputValue] = useState('')
  const [sending, setSending] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const connectWebSocket = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_API_HOST || window.location.hostname
    const port = import.meta.env.VITE_API_PORT || '8000'

    let url = `${protocol}//${host}:${port}/api/v1/ws/conversations/${encodeURIComponent(portfolioName)}`
    if (sourceFilter) {
      url += `?source=${encodeURIComponent(sourceFilter)}`
    }

    const ws = new WebSocket(url)

    ws.onopen = () => {
      console.log(`Connected to conversation: ${portfolioName}`)
      setConnected(true)
      setError(null)
    }

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data)

      if (message.type === 'initial') {
        setMessages(message.data || [])
        setLoading(false)
      } else if (message.type === 'message') {
        setMessages((prev) => [...prev, message.data])
      }
    }

    ws.onerror = (event) => {
      console.error('WebSocket error:', event)
      setError('Connection error')
    }

    ws.onclose = () => {
      console.log('Disconnected from conversation')
      setConnected(false)
      setTimeout(() => {
        connectWebSocket()
      }, 3000)
    }

    wsRef.current = ws
  }, [portfolioName, sourceFilter])

  useEffect(() => {
    connectWebSocket()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connectWebSocket])

  const formatMessageDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return 'Just now'
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    if (days < 7) return `${days}d ago`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const getMessageBgColor = (msgType?: string) => {
    switch (msgType) {
      case 'alert':
        return 'bg-red-900/20 border-red-800'
      case 'signal':
        return 'bg-blue-900/20 border-blue-800'
      case 'portfolio':
        return 'bg-purple-900/20 border-purple-800'
      case 'user':
        return 'bg-green-900/20 border-green-800'
      default:
        return 'bg-slate-800/50 border-slate-700'
    }
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !onSendMessage) return

    setSending(true)
    try {
      await onSendMessage(inputValue)
      setInputValue('')
    } catch (err) {
      console.error('Error sending message:', err)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex flex-col bg-slate-900/30 border border-slate-800 rounded-lg overflow-hidden h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between flex-shrink-0">
        <div>
          <h2 className="text-sm font-bold text-white">{title}</h2>
          {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
        </div>
        <div className="flex items-center gap-2">
          {showRefreshButton && (
            <button
              onClick={onRefresh}
              disabled={loading}
              className="px-2 py-1 text-xs bg-slate-800 hover:bg-slate-700 rounded transition disabled:opacity-50"
              title="Refresh"
            >
              ⟳
            </button>
          )}
          <div
            className={`w-2 h-2 rounded-full ${
              connected ? 'bg-green-500' : 'bg-red-500'
            }`}
            title={connected ? 'Connected' : 'Disconnected'}
          />
        </div>
      </div>

      {/* Messages */}
      <div className={`flex-1 overflow-y-auto p-4 space-y-3 ${maxHeight}`}>
        {loading && (
          <p className="text-xs text-slate-500 text-center py-4">Loading conversation...</p>
        )}

        {error && (
          <div className="bg-red-900/30 border border-red-800 rounded-lg p-3">
            <p className="text-xs text-red-300">{error}</p>
          </div>
        )}

        {!loading && messages.length === 0 && (
          <p className="text-xs text-slate-500 text-center py-8">No messages yet</p>
        )}

        {messages.map((msg, idx) => (
          <div key={msg.id || idx} className={`border rounded p-3 text-xs ${getMessageBgColor(msg.type)}`}>
            {/* Message Header */}
            <div className="mb-2">
              {msg.portfolio && (
                <div className="font-semibold text-white mb-1">
                  Portfolio: {msg.portfolio}
                  {msg.signal && (
                    <>
                      {' '}
                      <span className="text-red-400">⚠ {msg.signal}</span>
                    </>
                  )}
                </div>
              )}

              {/* Tickers */}
              {msg.tickers && msg.tickers.length > 0 && (
                <div className="flex gap-2 flex-wrap mb-2">
                  {msg.tickers.map((ticker) => (
                    <span
                      key={ticker}
                      className="px-2 py-1 bg-purple-600 text-white text-xs rounded font-medium"
                    >
                      {ticker}
                    </span>
                  ))}
                </div>
              )}

              {/* Content */}
              <div className="text-slate-300 whitespace-pre-wrap break-words">
                {msg.source === 'alert' ? (
                  <AlertMessageRenderer content={msg.content} />
                ) : (
                  msg.content
                )}
              </div>
            </div>

            {/* Embedded Widget */}
            {msg.widget && (
              <Suspense fallback={<div className="text-xs text-slate-400">Loading widget...</div>}>
                <WidgetRenderer widget={msg.widget} />
              </Suspense>
            )}

            {/* Timestamp */}
            <p className="text-slate-500 mt-2">{formatMessageDate(msg.datetime)}</p>
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      {onSendMessage && (
        <div className="px-4 py-3 border-t border-slate-800 flex-shrink-0">
          <div className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Type a message or command..."
              disabled={!connected || sending}
              className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded text-xs text-white placeholder-slate-500 disabled:opacity-50"
            />
            <button
              onClick={handleSendMessage}
              disabled={!connected || sending || !inputValue.trim()}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded text-xs font-medium disabled:opacity-50 transition"
            >
              {sending ? 'Sending...' : 'Send'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

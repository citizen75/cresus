import { useState, useEffect, useRef, useCallback } from 'react'
import { AlertMessageRenderer } from './AlertMessageRenderer'

interface ConversationMessage {
  source: string
  content: string
  datetime: string
}

interface ConversationWidgetProps {
  portfolioName: string
  sourceFilter?: string
  title?: string
  subtitle?: string
  showRefreshButton?: boolean
  onRefresh?: () => void
  maxHeight?: string
}

export function ConversationWidget({
  portfolioName,
  sourceFilter,
  title = 'Conversation',
  subtitle,
  showRefreshButton = true,
  onRefresh,
  maxHeight = 'h-96'
}: ConversationWidgetProps) {
  const [messages, setMessages] = useState<ConversationMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
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
      // Attempt to reconnect after 3 seconds
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
          <div key={idx} className="bg-slate-800/50 border border-slate-700 rounded p-3 text-xs">
            <div className="mb-2">
              {msg.source === 'alert' ? (
                <AlertMessageRenderer content={msg.content} />
              ) : (
                <div className="text-slate-300 whitespace-pre-wrap break-words">
                  {msg.content}
                </div>
              )}
            </div>
            <p className="text-slate-500">{formatMessageDate(msg.datetime)}</p>
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}

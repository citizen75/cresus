import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from 'react'
import { getApiBaseUrl } from '@/services/api'
import { AlertMessageRenderer } from '@/components/AlertMessageRenderer'

interface Message {
  source: 'user' | 'chatbot' | 'alert' | 'notification'
  content: string
  datetime: string
  portfolio?: string
}

interface GlobalConversationPanelProps {
  onClose?: () => void
  onAlertClick?: (ticker: string) => void
  onAlertGridClick?: (alertInfo: AlertInfo, alertId?: string) => void
  selectedAlertId?: string | null
}

const SOURCE_COLORS = {
  user: 'bg-blue-900/30 text-blue-300',
  chatbot: 'bg-purple-900/30 text-purple-300',
  alert: 'bg-red-900/30 text-red-300',
  notification: 'bg-amber-900/30 text-amber-300',
}

const SOURCE_ICONS = {
  user: '👤',
  chatbot: '🤖',
  alert: '⚠️',
  notification: '🔔',
}

interface AlertInfo {
  title: string
  portfolio?: string
  tickers: string[]
  content: string
}

function parseAlertContent(content: string): AlertInfo {
  const lines = content.split('\n')
  const info: AlertInfo = {
    title: '',
    portfolio: undefined,
    tickers: [],
    content,
  }

  for (const line of lines) {
    // Extract portfolio
    if (line.startsWith('**Portfolio:**')) {
      info.portfolio = line.replace('**Portfolio:**', '').trim()
    }
    // Extract title (line with alert emoji)
    if (line.includes('🚨') || line.includes('⚠️')) {
      const match = line.match(/\*\*([^*]+)\*\*/)
      if (match) {
        info.title = match[1]
      }
    }
    // Extract tickers from bullet points
    if (line.startsWith('  •')) {
      const match = line.match(/•\s+([A-Z0-9.-]+):/)
      if (match) {
        info.tickers.push(match[1])
      }
    }
  }

  return info
}

const GlobalConversationPanel = forwardRef<
  { scrollToBottom: () => void },
  GlobalConversationPanelProps
>(({ onClose, onAlertClick, onAlertGridClick, selectedAlertId }, ref) => {
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [newMessage, setNewMessage] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useImperativeHandle(ref, () => ({
    scrollToBottom: () => {
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
      }
    },
  }))

  useEffect(() => {
    const fetchMessages = async () => {
      try {
        setLoading(true)
        const baseUrl = getApiBaseUrl()
        const response = await fetch(
          `${baseUrl}/api/v1/conversations/_global`
        )
        if (!response.ok) {
          throw new Error('Failed to load conversations')
        }
        const data = await response.json()
        setMessages(data.history || [])
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading conversations')
      } finally {
        setLoading(false)
      }
    }

    fetchMessages()
  }, [])


  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newMessage.trim()) return

    try {
      setIsSubmitting(true)
      setError(null)

      const baseUrl = getApiBaseUrl()
      const url = `${baseUrl}/api/v1/conversations/_global/message`

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: 'user',
          content: newMessage,
        }),
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Failed to send message (${response.status}): ${errorText}`)
      }

      const data = await response.json()
      setMessages(data.history || [])
      setNewMessage('')
      setError(null)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Error sending message'
      setError(errorMsg)
    } finally {
      setIsSubmitting(false)
    }
  }

  const formatTime = (datetime: string) => {
    try {
      const date = new Date(datetime)
      const now = new Date()

      // Format time as HH:MM (24-hour format)
      const hours = String(date.getHours()).padStart(2, '0')
      const minutes = String(date.getMinutes()).padStart(2, '0')
      const timeStr = `${hours}:${minutes}`

      const diffMs = now.getTime() - date.getTime()
      const diffMins = Math.floor(diffMs / 60000)

      // For today's messages, just show time
      const isToday = date.toDateString() === now.toDateString()
      if (isToday) return timeStr

      // For other days, show date and time
      return date.toLocaleString([], {
        month: 'short',
        day: 'numeric'
      }) + ` ${timeStr}`
    } catch {
      return datetime
    }
  }

  const handleDeleteMessage = async (msg: Message) => {
    try {
      const baseUrl = getApiBaseUrl()
      const url = `${baseUrl}/api/v1/conversations/_global/message?timestamp=${encodeURIComponent(msg.datetime)}`

      const response = await fetch(url, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error(`Failed to delete message`)
      }

      const data = await response.json()
      setMessages(data.history || [])
      setError(null)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Error deleting message'
      setError(errorMsg)
    }
  }

  return (
    <div className="flex h-full bg-slate-900 rounded-lg border border-slate-800 flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">💬</span>
          <h3 className="text-sm font-semibold text-white">Global Chat</h3>
          <span className="text-xs text-slate-500">
            {messages.length}
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-400"
          >
            ✕
          </button>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="px-4 py-2 bg-red-900/30 border-b border-red-800">
          <div className="text-red-400 text-xs flex items-start gap-2">
            <span>⚠️</span>
            <div className="flex-1">{error}</div>
            <button
              onClick={() => setError(null)}
              className="text-red-400 hover:text-red-300"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Messages Container */}
      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-slate-400 text-sm">Loading conversations...</div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-slate-500 text-xs text-center">
              No messages yet. Start a conversation!
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => {
            const alertInfo = msg.source === 'alert' ? parseAlertContent(msg.content) : null
            const alertId = `${idx}-${msg.datetime}`
            const isSelected = selectedAlertId === alertId

            return (
              <div
                key={idx}
                className={`rounded-lg border transition-all ${
                  msg.source === 'alert'
                    ? `cursor-pointer hover:bg-slate-800/80 p-0 ${isSelected ? 'bg-slate-800 border-purple-600/50' : 'bg-slate-800/50 border-slate-700/50'}`
                    : 'p-3 space-y-1 bg-slate-800/50 border-slate-700/50'
                }`}
              >
                {msg.source === 'alert' && alertInfo ? (
                  // Alert Card View
                  <div className="space-y-0">
                    {/* Alert Header */}
                    <div className="bg-gradient-to-r from-rose-600/50 to-pink-600/50 border-b border-rose-500/40 p-3">
                      <div className="flex items-center justify-between">
                        <div
                          className="flex-1 flex items-center gap-3"
                          onClick={() => onAlertGridClick?.(alertInfo, alertId)}
                        >
                          {alertInfo.portfolio && (
                            <p className="text-xs text-rose-200 font-medium">
                              Portfolio: <span className="font-bold text-rose-100">{alertInfo.portfolio}</span>
                            </p>
                          )}
                          <p className="text-sm font-bold text-white">
                            ⚠️ {alertInfo.title} 🚨
                          </p>
                        </div>
                        <button
                          onClick={() => handleDeleteMessage(msg)}
                          className="text-slate-400 hover:text-rose-300 text-xs flex-shrink-0 transition"
                          title="Delete message"
                        >
                          ✕
                        </button>
                      </div>
                    </div>

                    {/* Tickers List - Compact */}
                    {alertInfo.tickers.length > 0 && (
                      <div className="border-t border-rose-500/30 px-3 py-3 bg-slate-800/80 flex items-center gap-2 flex-wrap">
                        <p className="text-xs text-rose-300 font-semibold">Tickers:</p>
                        {alertInfo.tickers.slice(0, 8).map((ticker) => (
                          <button
                            key={ticker}
                            onClick={() => {
                              if (onAlertClick) onAlertClick(ticker)
                            }}
                            className="px-2.5 py-1.5 bg-gradient-to-r from-purple-600/70 to-violet-600/70 hover:from-purple-500 hover:to-violet-500 text-white rounded text-xs font-semibold transition inline-block shadow-sm"
                            title={`View ${ticker} chart`}
                          >
                            📈 {ticker}
                          </button>
                        ))}
                        {alertInfo.tickers.length > 8 && (
                          <span className="text-xs text-slate-400 font-medium">+{alertInfo.tickers.length - 8} more</span>
                        )}
                      </div>
                    )}

                    {/* Timestamp */}
                    <div className="px-3 py-2 border-t border-rose-500/20 flex items-center justify-between bg-slate-900/70">
                      <span className="text-xs text-slate-400 font-medium">{formatTime(msg.datetime)}</span>
                    </div>
                  </div>
                ) : (
                  // Regular Message View
                  <>
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-xs font-medium px-2 py-1 rounded ${
                          SOURCE_COLORS[msg.source]
                        }`}
                      >
                        {SOURCE_ICONS[msg.source]} {msg.source}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-500">
                          {formatTime(msg.datetime)}
                        </span>
                        <button
                          onClick={() => handleDeleteMessage(msg)}
                          className="text-slate-500 hover:text-red-400 text-xs"
                          title="Delete message"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                    <div className="line-clamp-3 overflow-hidden">
                      <AlertMessageRenderer content={msg.content} />
                    </div>
                  </>
                )}
              </div>
            )
          })
        )}
      </div>

      {/* Input Area */}
      <form
        onSubmit={handleSendMessage}
        className="border-t border-slate-800 px-4 py-3 space-y-2"
      >
        <input
          type="text"
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          placeholder="Type a message..."
          disabled={isSubmitting}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-600 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isSubmitting || !newMessage.trim()}
          className="w-full px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-medium rounded transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? '⏳ Sending...' : '📤 Send'}
        </button>
      </form>
    </div>
  )
})

GlobalConversationPanel.displayName = 'GlobalConversationPanel'

export default GlobalConversationPanel

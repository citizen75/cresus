import { useState, useEffect } from 'react'
import { getApiBaseUrl } from '@/services/api'

interface Message {
  source: 'user' | 'chatbot' | 'alert' | 'notification'
  content: string
  datetime: string
}

interface ConversationPanelProps {
  portfolioName: string
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

export default function ConversationPanel({ portfolioName }: ConversationPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [newMessage, setNewMessage] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    const fetchMessages = async () => {
      try {
        setLoading(true)
        const baseUrl = getApiBaseUrl()
        const response = await fetch(
          `${baseUrl}/api/v1/conversations/${encodeURIComponent(portfolioName)}`
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
  }, [portfolioName])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newMessage.trim()) return
    if (!portfolioName) {
      setError('Portfolio name not available')
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)

      const baseUrl = getApiBaseUrl()
      const url = `${baseUrl}/api/v1/conversations/${encodeURIComponent(portfolioName)}/message`
      console.log('[ConversationPanel] Sending message to:', url)
      console.log('[ConversationPanel] Portfolio:', portfolioName)
      console.log('[ConversationPanel] Message:', { source: 'user', content: newMessage })

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: 'user',
          content: newMessage,
        }),
      })

      console.log('[ConversationPanel] Response status:', response.status)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('[ConversationPanel] API Error:', response.status, errorText)
        throw new Error(`Failed to send message (${response.status}): ${errorText}`)
      }

      const data = await response.json()
      console.log('[ConversationPanel] Response data:', data)
      setMessages(data.history || [])
      setNewMessage('')
      setError(null)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Error sending message'
      console.error('[ConversationPanel] Send error:', errorMsg, err)
      setError(errorMsg)
    } finally {
      setIsSubmitting(false)
    }
  }

  const formatTime = (datetime: string) => {
    try {
      const date = new Date(datetime)
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffMins = Math.floor(diffMs / 60000)

      if (diffMins < 1) return 'now'
      if (diffMins < 60) return `${diffMins}m ago`
      const diffHours = Math.floor(diffMins / 60)
      if (diffHours < 24) return `${diffHours}h ago`
      const diffDays = Math.floor(diffHours / 24)
      return `${diffDays}d ago`
    } catch {
      return datetime
    }
  }

  return (
    <div className="flex flex-col h-full bg-slate-900 rounded-lg border border-slate-800">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-lg">💬</span>
          <h3 className="text-sm font-semibold text-white">Conversations</h3>
          <span className="text-xs text-slate-500 ml-auto">
            {messages.length}
          </span>
        </div>
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
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
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
          messages.map((msg, idx) => (
            <div
              key={idx}
              className="rounded-lg p-3 bg-slate-800/50 border border-slate-700/50 space-y-1"
            >
              <div className="flex items-center justify-between">
                <span
                  className={`text-xs font-medium px-2 py-1 rounded ${
                    SOURCE_COLORS[msg.source]
                  }`}
                >
                  {SOURCE_ICONS[msg.source]} {msg.source}
                </span>
                <span className="text-xs text-slate-500">
                  {formatTime(msg.datetime)}
                </span>
              </div>
              <p className="text-xs text-slate-300 break-words line-clamp-3">
                {msg.content}
              </p>
            </div>
          ))
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
}

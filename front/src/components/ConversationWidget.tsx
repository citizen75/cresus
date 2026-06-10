import { useState, useEffect, useRef, useCallback, Suspense } from 'react'
import { AlertMessageRenderer } from './AlertMessageRenderer'
import { getApiBaseUrl } from '@/services/api'
import { useConversation, type ConversationMessage } from '@/contexts/ConversationContext'

interface MessageWidget {
  type: 'portfolio_holdings' | 'portfolio_positions' | 'market_overview' | 'trade_analysis'
  data: Record<string, any>
}

// Parse alert content to extract portfolio, signal, and tickers
function parseAlertContent(content: string): { portfolio?: string; signal?: string; tickers: string[] } {
  const result = { portfolio: undefined, signal: undefined, tickers: [] }
  const lines = content.split('\n')

  for (const line of lines) {
    // Extract portfolio: **Portfolio:** xxx
    if (line.startsWith('**Portfolio:**')) {
      result.portfolio = line.replace('**Portfolio:**', '').trim()
    }
    // Extract signal from line with emoji: ⚠️ **sha_red** OR ⚠️ sha_red
    if ((line.includes('🚨') || line.includes('⚠️'))) {
      // Try bold markdown format first: ⚠️ **signal**
      let match = line.match(/\*\*([^*]+)\*\*/)
      if (match) {
        result.signal = match[1]
      } else {
        // Try plain format: ⚠️ signal_name
        match = line.match(/(⚠️|🚨)\s+(.+)$/)
        if (match) {
          result.signal = match[2].trim()
        }
      }
    }
    // Extract tickers from bullet points: • AAPL: xxx
    if (line.trim().startsWith('•')) {
      const match = line.match(/•\s+([A-Z0-9.-]+)/)
      if (match) {
        result.tickers.push(match[1])
      }
    }
    // Extract tickers from arrows: ◀ AAPL
    if (line.trim().startsWith('◀')) {
      const match = line.match(/◀\s+([A-Z0-9.-]+)/)
      if (match) {
        result.tickers.push(match[1])
      }
    }
  }

  return result
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
  onPortfolioClick?: (portfolioName: string, tickers: string[], widget?: MessageWidget) => void
  onNewMessage?: (message: ConversationMessage) => void
  autoSelectLatestAlert?: boolean // Auto-select latest alert in right panel
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

    case 'results_widget':
      return (
        <div className="mt-2 bg-slate-700/30 rounded p-2 border border-slate-600">
          <div className="text-xs font-semibold text-slate-300 mb-2">Alert Results:</div>
          <div className="text-xs text-slate-400">
            <p>Click message to view full results</p>
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
  onSendMessage,
  onPortfolioClick,
  onNewMessage,
  autoSelectLatestAlert = false
}: ConversationWidgetProps) {
  const { messages: allMessages, connected: allConnected, loading: allLoading, error: allError, subscribeToConversation, unsubscribeFromConversation, deleteMessage } = useConversation()
  const [inputValue, setInputValue] = useState('')
  const [sending, setSending] = useState(false)
  const [selectedMessage, setSelectedMessage] = useState<any>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const conversationKeyRef = useRef<string>('')

  // Get messages for this specific conversation
  const key = sourceFilter ? `${portfolioName}:${sourceFilter}` : portfolioName
  const messages = allMessages[key] || []
  const loading = allLoading[key] || false
  const connected = allConnected[key] || false
  const error = allError[key] || null

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Subscribe to conversation (keep open across page changes)
  useEffect(() => {
    conversationKeyRef.current = key
    console.log(`[ConversationWidget] Subscribing to: ${key}`)
    subscribeToConversation(portfolioName, sourceFilter, onNewMessage)

    // Don't unsubscribe on unmount - keep connection alive across pages!
    // Only cleanup the callback listener if component unmounts
    return () => {
      console.log(`[ConversationWidget] Component unmounting: ${key} (connection stays open)`)
    }
  }, [portfolioName, sourceFilter, subscribeToConversation, onNewMessage])

  // Auto-select latest alert message if enabled
  useEffect(() => {
    if (autoSelectLatestAlert && messages.length > 0) {
      // Find the most recent alert message with results_widget
      const latestAlert = [...messages].reverse().find(msg => msg.widget === 'results_widget' && msg.data?.results)
      if (latestAlert) {
        setSelectedMessage(latestAlert)
      }
    }
  }, [autoSelectLatestAlert, messages])

  const formatMessageDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  }

  // Removed getMessageBgColor - using inline styles now for compact format

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

      {/* Main Content - Messages + Results Panel */}
      <div className="flex-1 flex overflow-hidden">
        {/* Messages */}
        <div className={`${selectedMessage ? 'flex-0 w-1/3' : 'flex-1'} overflow-y-auto p-4 space-y-3 transition-all ${maxHeight}`}>
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

        {messages.map((msg, idx) => {
          // Parse alert content to extract structured data
          const parsedAlert = msg.source === 'alert' ? parseAlertContent(msg.content) : null
          const portfolio = msg.portfolio || parsedAlert?.portfolio
          const signal = msg.signal || parsedAlert?.signal
          const tickers = msg.tickers || parsedAlert?.tickers || []

          const handleMessageClick = () => {
            // If message has results_widget, show ResultsWidget on right panel (regardless of portfolio)
            if (msg.widget === 'results_widget') {
              setSelectedMessage(msg)
            } else if (portfolio && portfolio !== 'global' && onPortfolioClick) {
              onPortfolioClick(portfolio, tickers, msg.widget)
            }
          }

          const handleDeleteMessage = async (e: React.MouseEvent) => {
            e.stopPropagation()
            try {
              const messageId = msg.id || msg.datetime // Fallback to datetime for backward compatibility
              console.log(`[Delete Message] Deleting: ${portfolioName}/${messageId}`)
              await deleteMessage(portfolioName, messageId)
              console.log(`[Delete Message] Success`)
            } catch (err) {
              console.error('[Delete Message] Error:', err)
            }
          }

          return (
            <div
              key={`${msg.datetime}-${idx}`}
              className="rounded-lg p-3 bg-slate-800/50 border border-slate-700/50 space-y-2 cursor-pointer hover:bg-slate-700/50 transition group"
              onClick={handleMessageClick}
            >
              {/* Header: Icon + Portfolio + Signal + Time + Delete */}
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-slate-300">
                    {signal ? '⚠️' : msg.source === 'alert' ? '🔔' : '💬'} {portfolio || 'Global'}
                    {signal && <span className="text-red-400 ml-1">{signal}</span>}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">{formatMessageDate(msg.datetime)}</span>
                  <button
                    onClick={handleDeleteMessage}
                    className="text-slate-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition text-sm font-bold"
                    title="Delete message"
                  >
                    ✕
                  </button>
                </div>
              </div>

              {/* Tickers (compact inline) */}
              {tickers.length > 0 && (
                <div className="flex gap-1 flex-wrap">
                  {tickers.map((ticker) => (
                    <span
                      key={ticker}
                      className="px-2 py-0.5 bg-purple-600/80 text-white text-xs rounded font-semibold"
                    >
                      ◀ {ticker}
                    </span>
                  ))}
                </div>
              )}

              {/* Content Preview (only for non-alerts) */}
              {msg.source !== 'alert' && (
                <div className="text-xs text-slate-300 line-clamp-2">{msg.content}</div>
              )}

              {/* Embedded Widget */}
              {msg.widget && (
                <Suspense fallback={<div className="text-xs text-slate-400">Loading widget...</div>}>
                  <WidgetRenderer widget={msg.widget} />
                </Suspense>
              )}
            </div>
          )
        })}

        <div ref={messagesEndRef} />
        </div>

        {/* Results Widget Panel */}
        {selectedMessage && selectedMessage.widget === 'results_widget' && selectedMessage.data?.results && (
          <div className="flex-1 border-l border-slate-800 overflow-hidden flex flex-col bg-slate-900/30">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 flex-shrink-0">
              <h3 className="text-sm font-semibold text-white">Alert Results</h3>
              <button
                onClick={() => setSelectedMessage(null)}
                className="text-slate-400 hover:text-white transition"
              >
                ✕
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <div className="space-y-4">
                {/* Alert Header */}
                <div className="border-b border-slate-700 pb-3">
                  <div className="text-sm font-semibold text-white mb-1">⚠️ {selectedMessage.data.alert_name}</div>
                  <div className="text-xs text-slate-400">
                    {selectedMessage.data.results.length} matches found
                  </div>
                </div>

                {/* Results List */}
                <div className="space-y-2">
                  {selectedMessage.data.results.map((result: any, idx: number) => (
                    <div key={idx} className="bg-slate-800/50 rounded p-2 border border-slate-700">
                      <div className="text-sm font-medium text-white">{result.ticker}</div>
                      {result.company_name && result.company_name !== result.ticker && (
                        <div className="text-xs text-slate-400 mt-1">{result.company_name}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
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

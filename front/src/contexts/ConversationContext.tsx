import { createContext, useContext, useEffect, useRef, useState, ReactNode, useCallback } from 'react'
import { getApiBaseUrl } from '@/services/api'

export interface ConversationMessage {
  id?: string
  type?: 'alert' | 'signal' | 'portfolio' | 'llm' | 'user'
  source: string
  content: string
  datetime: string
  portfolio?: string
  signal?: string
  tickers?: string[]
  widget?: any
}

interface WebSocketConnection {
  ws: WebSocket
  portfolioName: string
  sourceFilter?: string
  listeners: Set<(msg: ConversationMessage) => void>
  initialDataLoaded: boolean
}

interface ConversationContextType {
  messages: Record<string, ConversationMessage[]> // Key: "portfolio:source" or "portfolio"
  connected: Record<string, boolean> // Key: "portfolio:source" or "portfolio"
  loading: Record<string, boolean>
  error: Record<string, string | null>
  subscribeToConversation: (
    portfolioName: string,
    sourceFilter?: string,
    callback?: (msg: ConversationMessage) => void
  ) => void
  unsubscribeFromConversation: (portfolioName: string, sourceFilter?: string) => void
  deleteMessage: (portfolioName: string, messageId: string) => Promise<void>
}

const ConversationContext = createContext<ConversationContextType | undefined>(undefined)

export function ConversationProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<Record<string, ConversationMessage[]>>({})
  const [connected, setConnected] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<Record<string, string | null>>({})

  const connectionsRef = useRef<Map<string, WebSocketConnection>>(new Map())

  const getKey = (portfolioName: string, sourceFilter?: string) => {
    return sourceFilter ? `${portfolioName}:${sourceFilter}` : portfolioName
  }

  const connectWebSocket = useCallback(
    (portfolioName: string, sourceFilter?: string, callback?: (msg: ConversationMessage) => void) => {
      const key = getKey(portfolioName, sourceFilter)

      // If already connected, just add listener
      if (connectionsRef.current.has(key)) {
        const conn = connectionsRef.current.get(key)!
        if (callback) {
          conn.listeners.add(callback)
        }
        return
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const baseUrl = getApiBaseUrl().replace(/^https?:\/\//, '')
      let url = `${protocol}//${baseUrl}/api/v1/ws/conversations/${encodeURIComponent(portfolioName)}`
      if (sourceFilter) {
        url += `?source=${encodeURIComponent(sourceFilter)}`
      }

      console.log(`[ConversationContext] Connecting to: ${url}`)
      setLoading((prev) => ({ ...prev, [key]: true }))
      setConnected((prev) => ({ ...prev, [key]: false }))

      const ws = new WebSocket(url)
      const listeners = new Set<(msg: ConversationMessage) => void>()
      if (callback) {
        listeners.add(callback)
      }

      ws.onopen = () => {
        console.log(`[ConversationContext] Connected to: ${portfolioName}`)
        setConnected((prev) => ({ ...prev, [key]: true }))
        setError((prev) => ({ ...prev, [key]: null }))
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)

          if (message.type === 'initial') {
            setMessages((prev) => ({ ...prev, [key]: message.data || [] }))
            const conn = connectionsRef.current.get(key)
            if (conn) {
              conn.initialDataLoaded = true
            }
            setLoading((prev) => ({ ...prev, [key]: false }))
          } else if (message.type === 'message') {
            setMessages((prev) => ({
              ...prev,
              [key]: [...(prev[key] || []), message.data],
            }))
            // Notify all listeners
            const conn = connectionsRef.current.get(key)
            if (conn) {
              conn.listeners.forEach((listener) => listener(message.data))
            }
          }
        } catch (err) {
          console.error('[ConversationContext] Error parsing message:', err)
        }
      }

      ws.onerror = (event) => {
        console.error('[ConversationContext] WebSocket error:', event)
        setError((prev) => ({ ...prev, [key]: 'Connection error' }))
      }

      ws.onclose = () => {
        console.log(`[ConversationContext] Disconnected from: ${portfolioName}`)
        setConnected((prev) => ({ ...prev, [key]: false }))
        connectionsRef.current.delete(key)

        // Reconnect after 3 seconds
        setTimeout(() => {
          connectWebSocket(portfolioName, sourceFilter, callback)
        }, 3000)
      }

      connectionsRef.current.set(key, {
        ws,
        portfolioName,
        sourceFilter,
        listeners,
        initialDataLoaded: false,
      })
    },
    []
  )

  const subscribeToConversation = useCallback(
    (portfolioName: string, sourceFilter?: string, callback?: (msg: ConversationMessage) => void) => {
      connectWebSocket(portfolioName, sourceFilter, callback)
    },
    [connectWebSocket]
  )

  const unsubscribeFromConversation = useCallback((portfolioName: string, sourceFilter?: string) => {
    const key = getKey(portfolioName, sourceFilter)
    const conn = connectionsRef.current.get(key)
    if (conn) {
      conn.ws.close()
      connectionsRef.current.delete(key)
    }
    setMessages((prev) => {
      const newMessages = { ...prev }
      delete newMessages[key]
      return newMessages
    })
    setConnected((prev) => {
      const newConnected = { ...prev }
      delete newConnected[key]
      return newConnected
    })
  }, [])

  const deleteMessage = useCallback(async (portfolioName: string, messageId: string) => {
    try {
      const baseUrl = getApiBaseUrl()
      const response = await fetch(
        `${baseUrl}/api/v1/conversations/${encodeURIComponent(portfolioName)}/message?message_id=${encodeURIComponent(messageId)}`,
        { method: 'DELETE' }
      )

      if (response.ok) {
        // Remove from all keys that match this portfolio
        setMessages((prev) => {
          const newMessages = { ...prev }
          Object.keys(newMessages).forEach((key) => {
            if (key === portfolioName || key.startsWith(`${portfolioName}:`)) {
              newMessages[key] = newMessages[key].filter((m) => m.id !== messageId)
            }
          })
          return newMessages
        })
      } else {
        throw new Error(`Failed to delete message: ${response.status}`)
      }
    } catch (err) {
      console.error('[ConversationContext] Error deleting message:', err)
      throw err
    }
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      connectionsRef.current.forEach((conn) => conn.ws.close())
      connectionsRef.current.clear()
    }
  }, [])

  const value: ConversationContextType = {
    messages,
    connected,
    loading,
    error,
    subscribeToConversation,
    unsubscribeFromConversation,
    deleteMessage,
  }

  return <ConversationContext.Provider value={value}>{children}</ConversationContext.Provider>
}

export function useConversation() {
  const context = useContext(ConversationContext)
  if (!context) {
    throw new Error('useConversation must be used within ConversationProvider')
  }
  return context
}

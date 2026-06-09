import { useState, useCallback, useRef, useEffect } from 'react'
import { ConversationMessage, WebSocketMessage } from '../types/conversation'

interface UseConversationOptions {
  portfolioName: string
  sourceFilter?: string
  autoConnect?: boolean
}

export function useConversation(options: UseConversationOptions) {
  const { portfolioName, sourceFilter, autoConnect = true } = options
  const [messages, setMessages] = useState<ConversationMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_API_HOST || window.location.hostname
    const port = import.meta.env.VITE_API_PORT || '8000'

    let url = `${protocol}//${host}:${port}/api/v1/ws/conversations/${encodeURIComponent(portfolioName)}`
    if (sourceFilter) {
      url += `?source=${encodeURIComponent(sourceFilter)}`
    }

    try {
      const ws = new WebSocket(url)

      ws.onopen = () => {
        console.log(`Connected to conversation: ${portfolioName}`)
        setConnected(true)
        setError(null)
        setLoading(false)
      }

      ws.onmessage = (event) => {
        const message: WebSocketMessage = JSON.parse(event.data)

        if (message.type === 'initial') {
          setMessages(message.data as ConversationMessage[])
          setLoading(false)
        } else if (message.type === 'message') {
          setMessages((prev) => [...prev, message.data as ConversationMessage])
        } else if (message.type === 'error') {
          setError(message.message || 'Unknown error')
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
        if (autoConnect) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, 3000)
        }
      }

      wsRef.current = ws
    } catch (err) {
      console.error('Failed to connect:', err)
      setError('Failed to connect')
      setLoading(false)
    }
  }, [portfolioName, sourceFilter, autoConnect])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
    }
  }, [])

  const sendMessage = useCallback(
    async (content: string) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        throw new Error('Not connected')
      }

      const message: ConversationMessage = {
        type: 'user',
        source: 'user',
        content,
        datetime: new Date().toISOString(),
      }

      wsRef.current.send(JSON.stringify(message))
    },
    []
  )

  useEffect(() => {
    if (autoConnect) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [autoConnect, connect, disconnect])

  return {
    messages,
    loading,
    connected,
    error,
    sendMessage,
    connect,
    disconnect,
    clear: () => setMessages([]),
  }
}

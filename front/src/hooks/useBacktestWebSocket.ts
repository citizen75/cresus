import { useEffect, useState, useCallback, useRef } from 'react'

export interface BacktestMessage {
  type: 'daily_results' | 'backtest_complete' | 'error'
  backtest_id: string
  strategy_name: string
  timestamp: string
  data: Record<string, any>
}

interface UseBacktestWebSocketOptions {
  backtest_id: string
  strategy_name?: string
  enabled?: boolean
}

export function useBacktestWebSocket(options: UseBacktestWebSocketOptions) {
  const { backtest_id, strategy_name = '', enabled = true } = options

  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<BacktestMessage | null>(null)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const connect = useCallback(() => {
    if (!enabled || !backtest_id) return

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const host = window.location.hostname
      const port = window.location.port ? `:${window.location.port}` : ''
      const url = `${protocol}://${host}${port}/api/v1/ws/backtest/${backtest_id}${strategy_name ? `?strategy=${strategy_name}` : ''}`

      const ws = new WebSocket(url)

      ws.onopen = () => {
        console.log(`WebSocket connected to backtest ${backtest_id}`)
        setIsConnected(true)
        setError(null)
      }

      ws.onmessage = (event) => {
        try {
          // Handle both JSON string and JSON object messages
          const data = typeof event.data === 'string'
            ? JSON.parse(event.data)
            : event.data

          // If the data is a JSON string, parse it again
          const message: BacktestMessage = typeof data === 'string'
            ? JSON.parse(data)
            : data

          setLastMessage(message)
          console.log(`Backtest message: ${message.type}`, message)
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e, event.data)
        }
      }

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        setError('WebSocket connection error')
        setIsConnected(false)
      }

      ws.onclose = () => {
        console.log(`WebSocket disconnected from backtest ${backtest_id}`)
        setIsConnected(false)

        // Attempt to reconnect after 3 seconds
        if (enabled && backtest_id) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, 3000)
        }
      }

      wsRef.current = ws
    } catch (e) {
      console.error('Failed to create WebSocket:', e)
      setError('Failed to create WebSocket connection')
      setIsConnected(false)
    }
  }, [backtest_id, strategy_name, enabled])

  useEffect(() => {
    if (enabled && backtest_id) {
      connect()
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [backtest_id, enabled, connect])

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    setIsConnected(false)
  }, [])

  return {
    isConnected,
    lastMessage,
    error,
    disconnect,
  }
}

/**
 * Conversation Widget Types
 * Defines message structures for real-time alerts, signals, portfolio updates, and LLM chat
 */

export type MessageType = 'alert' | 'signal' | 'portfolio' | 'llm' | 'user'
export type WidgetType = 'portfolio_holdings' | 'portfolio_positions' | 'market_overview' | 'trade_analysis'

export interface MessageWidget {
  type: WidgetType
  data: Record<string, any>
}

export interface ConversationMessage {
  id?: string
  type?: MessageType
  source: string
  content: string
  datetime: string

  // Alert/Signal context
  portfolio?: string
  signal?: string
  tickers?: string[]

  // Embedded widget
  widget?: MessageWidget
}

// Example message structures

export const EXAMPLE_ALERT_MESSAGE: ConversationMessage = {
  id: 'msg_1',
  type: 'alert',
  source: 'alert',
  content: 'SHA indicator turned RED on 5 tickers',
  datetime: new Date().toISOString(),
  portfolio: 'Nathalie PEA',
  signal: 'sha_red',
  tickers: ['PASI.PA', 'EXS1.AS', 'ENGI.PA', 'NK.PA', 'SU.PA'],
}

export const EXAMPLE_PORTFOLIO_UPDATE: ConversationMessage = {
  id: 'msg_2',
  type: 'portfolio',
  source: 'portfolio',
  content: 'Portfolio balance updated',
  datetime: new Date().toISOString(),
  portfolio: 'Main Portfolio',
  widget: {
    type: 'portfolio_holdings',
    data: {
      holdings: [
        { ticker: 'AAPL', shares: 100, price: 150.25, value: 15025 },
        { ticker: 'MSFT', shares: 50, price: 380.50, value: 19025 },
        { ticker: 'GOOGL', shares: 25, price: 2800.00, value: 70000 },
      ],
    },
  },
}

export const EXAMPLE_LLM_RESPONSE: ConversationMessage = {
  id: 'msg_3',
  type: 'llm',
  source: 'llm',
  content: 'Based on current market conditions, I recommend scaling out of AAPL with a 2% trailing stop. The RSI is overbought and we are approaching resistance.',
  datetime: new Date().toISOString(),
}

export const EXAMPLE_USER_COMMAND: ConversationMessage = {
  id: 'msg_4',
  type: 'user',
  source: 'user',
  content: '/analyze AAPL',
  datetime: new Date().toISOString(),
}

// Backend WebSocket message format
export interface WebSocketMessage {
  type: 'initial' | 'message' | 'error'
  data?: ConversationMessage | ConversationMessage[]
  message?: string
}

// Supported commands
export const SUPPORTED_COMMANDS = [
  { cmd: '/analyze TICKER', desc: 'Analyze a specific ticker' },
  { cmd: '/status', desc: 'Get portfolio status' },
  { cmd: '/alerts', desc: 'Show active alerts' },
  { cmd: '/positions', desc: 'Show current positions' },
  { cmd: '/help', desc: 'Show available commands' },
]

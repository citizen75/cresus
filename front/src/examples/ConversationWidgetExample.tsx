/**
 * ConversationWidget Usage Examples
 *
 * Shows how to integrate the conversation widget with real-time alerts, signals, portfolio updates, and LLM chat
 */

import { ConversationWidget } from '../components/ConversationWidget'
import { useConversation } from '../hooks/useConversation'

/**
 * Basic usage - embedded in a page
 */
export function BasicConversationExample() {
  return (
    <div className="w-full h-screen">
      <ConversationWidget
        portfolioName="Nathalie PEA"
        title="Global Chat"
        subtitle="Real-time alerts, signals & portfolio updates"
      />
    </div>
  )
}

/**
 * With user input and message sending
 */
export function InteractiveConversationExample() {
  const { sendMessage, connected, messages } = useConversation({
    portfolioName: 'Main Portfolio',
  })

  const handleSendMessage = async (message: string) => {
    await sendMessage(message)
  }

  return (
    <div className="w-full h-screen">
      <ConversationWidget
        portfolioName="Main Portfolio"
        title="Trading Assistant"
        onSendMessage={handleSendMessage}
      />
    </div>
  )
}

/**
 * Multiple conversations side-by-side
 */
export function MultiPortfolioConversationExample() {
  const portfolios = ['Nathalie PEA', 'Victoria PEA', 'BNP Portfolio']

  return (
    <div className="grid grid-cols-3 gap-4 w-full h-screen p-4">
      {portfolios.map((portfolio) => (
        <ConversationWidget
          key={portfolio}
          portfolioName={portfolio}
          title={portfolio}
          subtitle="Alerts & signals"
          maxHeight="h-full"
        />
      ))}
    </div>
  )
}

/**
 * Filtered conversations (alerts only)
 */
export function AlertsOnlyExample() {
  return (
    <div className="w-1/2 h-screen">
      <ConversationWidget
        portfolioName="Main Portfolio"
        sourceFilter="alert"
        title="Alerts"
        subtitle="Real-time alerts only"
      />
    </div>
  )
}

/**
 * With custom handling of messages
 */
export function CustomHandlerExample() {
  const { messages, sendMessage, loading } = useConversation({
    portfolioName: 'Trading Bot',
  })

  const handleAlertClick = (message: any) => {
    if (message.tickers) {
      // Navigate to ticker analysis or trigger trade
      console.log('Alert clicked for tickers:', message.tickers)
    }
  }

  return (
    <div className="w-full h-screen">
      <ConversationWidget
        portfolioName="Trading Bot"
        title="Trading Commands"
        onSendMessage={sendMessage}
      />

      {/* Show alert count */}
      <div className="mt-4 p-4 bg-slate-900 rounded">
        <p className="text-sm text-slate-300">
          Total messages: {messages.length} | Loading: {loading ? 'yes' : 'no'}
        </p>
        <p className="text-sm text-slate-400">
          Alerts: {messages.filter((m) => m.type === 'alert').length}
        </p>
      </div>
    </div>
  )
}

/**
 * Message structure examples for backend integration
 *
 * Message types:
 * - alert: sha_red, signal triggered, etc.
 * - signal: buy/sell signals
 * - portfolio: portfolio updates, positions, balance changes
 * - llm: responses from LLM/trading bot
 * - user: user commands and queries
 *
 * Optional widgets:
 * - portfolio_holdings: list of current holdings
 * - portfolio_positions: open positions with PnL
 * - market_overview: market data and overview
 * - trade_analysis: entry/target/stop analysis
 */
export const BACKEND_MESSAGE_EXAMPLES = {
  // Alert with tickers
  alert_example: {
    type: 'alert',
    source: 'alert',
    content: 'SHA indicator turned RED',
    datetime: new Date().toISOString(),
    portfolio: 'Nathalie PEA',
    signal: 'sha_red',
    tickers: ['PASI.PA', 'EXS1.AS'],
  },

  // Portfolio update with widget
  portfolio_update_example: {
    type: 'portfolio',
    source: 'portfolio',
    content: 'Portfolio balance updated: +$1,250',
    datetime: new Date().toISOString(),
    portfolio: 'Main Portfolio',
    widget: {
      type: 'portfolio_holdings',
      data: {
        total_value: 125000,
        cash: 25000,
        holdings: [
          { ticker: 'AAPL', shares: 100, price: 150.25 },
          { ticker: 'MSFT', shares: 50, price: 380.50 },
        ],
      },
    },
  },

  // Trade analysis with entry/target/stop
  trade_analysis_example: {
    type: 'signal',
    source: 'signal',
    content: 'Trade setup identified on AAPL',
    datetime: new Date().toISOString(),
    tickers: ['AAPL'],
    widget: {
      type: 'trade_analysis',
      data: {
        entry_price: 150.0,
        target_price: 157.5,
        stop_loss: 147.0,
        rr_ratio: 2.5,
      },
    },
  },

  // LLM response
  llm_response_example: {
    type: 'llm',
    source: 'llm',
    content: 'Based on the SHA_RED signal and overbought RSI, I recommend taking profits on AAPL. The risk/reward is no longer favorable.',
    datetime: new Date().toISOString(),
  },

  // User command
  user_command_example: {
    type: 'user',
    source: 'user',
    content: '/analyze AAPL',
    datetime: new Date().toISOString(),
  },
}

/**
 * Supported commands for the trading bot:
 * /analyze TICKER - Analyze a ticker
 * /status - Get portfolio status
 * /alerts - Show active alerts
 * /positions - Show positions
 * /help - Show commands
 * /buy TICKER SHARES - Place buy order (requires confirmation)
 * /sell TICKER SHARES - Place sell order (requires confirmation)
 */

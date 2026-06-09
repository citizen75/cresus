# Conversation Widget

A real-time conversation/chat widget for displaying alerts, signals, portfolio updates, and LLM responses with support for embedded data widgets.

## Features

✅ **Real-time Updates** - WebSocket connection for streaming alerts and messages
✅ **Multiple Message Types** - Alerts, signals, portfolio updates, LLM responses, user commands
✅ **Embedded Widgets** - Inline data visualization (holdings, positions, trade analysis)
✅ **User Interaction** - Send commands and queries to the trading bot
✅ **Auto-reconnect** - Automatic reconnection on connection loss
✅ **Rich UI** - Color-coded messages, tickers as badges, timestamps

## Usage

### Basic Usage

```tsx
import { ConversationWidget } from '@/components/ConversationWidget'

export function MyPage() {
  return (
    <ConversationWidget
      portfolioName="Nathalie PEA"
      title="Global Chat"
      subtitle="Real-time alerts & signals"
    />
  )
}
```

### With User Input

```tsx
import { ConversationWidget } from '@/components/ConversationWidget'

export function TradingAssistant() {
  const handleSendMessage = async (message: string) => {
    // Send to backend LLM or command handler
    const response = await fetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    })
  }

  return (
    <ConversationWidget
      portfolioName="Main Portfolio"
      title="Trading Bot"
      onSendMessage={handleSendMessage}
    />
  )
}
```

### Using the Hook

```tsx
import { useConversation } from '@/hooks/useConversation'

export function ChatComponent() {
  const {
    messages,
    loading,
    connected,
    sendMessage,
  } = useConversation({
    portfolioName: 'Main Portfolio',
    sourceFilter: 'alert', // Optional: filter by source
  })

  return (
    <div>
      {/* Your custom UI using messages and handlers */}
    </div>
  )
}
```

## Message Types

### Alert Message
```typescript
{
  type: 'alert',
  source: 'alert',
  content: 'SHA indicator turned RED',
  datetime: '2026-06-09T14:26:00Z',
  portfolio: 'Nathalie PEA',
  signal: 'sha_red',
  tickers: ['PASI.PA', 'EXS1.AS'],
}
```

### Signal Message with Trade Analysis Widget
```typescript
{
  type: 'signal',
  source: 'signal',
  content: 'Trade setup identified',
  datetime: '2026-06-09T14:26:00Z',
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
}
```

### Portfolio Update with Holdings Widget
```typescript
{
  type: 'portfolio',
  source: 'portfolio',
  content: 'Portfolio updated',
  datetime: '2026-06-09T14:26:00Z',
  portfolio: 'Main Portfolio',
  widget: {
    type: 'portfolio_holdings',
    data: {
      holdings: [
        { ticker: 'AAPL', shares: 100, price: 150.25 },
        { ticker: 'MSFT', shares: 50, price: 380.50 },
      ],
    },
  },
}
```

### LLM Response
```typescript
{
  type: 'llm',
  source: 'llm',
  content: 'Based on current conditions, I recommend...',
  datetime: '2026-06-09T14:26:00Z',
}
```

### User Command
```typescript
{
  type: 'user',
  source: 'user',
  content: '/analyze AAPL',
  datetime: '2026-06-09T14:26:00Z',
}
```

## Widget Types

### portfolio_holdings
Displays a list of current holdings with shares and prices.

```typescript
{
  type: 'portfolio_holdings',
  data: {
    holdings: [
      { ticker: 'AAPL', shares: 100, price: 150.25, value: 15025 },
      { ticker: 'MSFT', shares: 50, price: 380.50, value: 19025 },
    ],
  },
}
```

### portfolio_positions
Shows open positions with PnL.

```typescript
{
  type: 'portfolio_positions',
  data: {
    positions: [
      { ticker: 'AAPL', entry: 148.0, current: 150.25, pnl: 1.52 },
      { ticker: 'MSFT', entry: 375.0, current: 380.50, pnl: 1.47 },
    ],
  },
}
```

### trade_analysis
Displays entry, target, stop loss, and risk/reward.

```typescript
{
  type: 'trade_analysis',
  data: {
    entry_price: 150.0,
    target_price: 157.5,
    stop_loss: 147.0,
    rr_ratio: 2.5,
  },
}
```

### market_overview
Market overview data (extensible).

## API Integration

The widget expects a WebSocket endpoint at:
```
ws://localhost:8000/api/v1/ws/conversations/{portfolioName}?source={sourceFilter}
```

### WebSocket Message Format

**Server → Client (initial load):**
```json
{
  "type": "initial",
  "data": [
    { "type": "alert", "source": "alert", "content": "...", "datetime": "..." },
    { "type": "llm", "source": "llm", "content": "...", "datetime": "..." }
  ]
}
```

**Server → Client (new message):**
```json
{
  "type": "message",
  "data": {
    "type": "alert",
    "source": "alert",
    "content": "SHA turned RED",
    "datetime": "2026-06-09T14:26:00Z",
    "portfolio": "Nathalie PEA",
    "signal": "sha_red",
    "tickers": ["PASI.PA"]
  }
}
```

**Client → Server (user message):**
```json
{
  "type": "user",
  "source": "user",
  "content": "/analyze AAPL",
  "datetime": "2026-06-09T14:26:00Z"
}
```

## Styling

The widget uses Tailwind CSS with dark theme colors:
- `bg-slate-900/30` - Main background
- `bg-red-900/20` - Alert messages
- `bg-blue-900/20` - Signal messages
- `bg-purple-900/20` - Portfolio messages
- `bg-green-900/20` - User messages
- `bg-purple-600` - Ticker badges

## Customization

All message styling is controlled by the `getMessageBgColor()` function. Extend it to add custom message types or colors.

## Examples

See `/front/src/examples/ConversationWidgetExample.tsx` for complete usage examples including:
- Basic embedded widget
- Interactive with user input
- Multiple portfolios side-by-side
- Filtered conversations (alerts only)
- Custom message handling

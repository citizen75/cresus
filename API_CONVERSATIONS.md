# Conversation API Documentation

## Overview

The Conversation API provides endpoints for managing portfolio-specific message storage and retrieval. Messages are stored per portfolio with support for different source types (user, chatbot, alert, notification).

**Base URL:** `/api/v1/conversations`

---

## Endpoints

### 1. Get Conversation History
**GET** `/{portfolio_name}`

Retrieve conversation history with pagination and filtering.

**Query Parameters:**
- `limit` (integer, optional): Max messages to return (1-1000)
- `offset` (integer, optional): Starting position (default: 0)
- `source` (string, optional): Filter by source (user|chatbot|alert|notification)
- `search` (string, optional): Search in message content

**Response:**
```json
{
  "portfolio_name": "PEA",
  "history": [
    {
      "source": "user",
      "content": "Buy signal on AAPL",
      "datetime": "2026-05-26T14:30:00"
    }
  ],
  "count": 1,
  "limit": null,
  "offset": 0,
  "total": 1
}
```

**Example:**
```bash
curl "http://localhost:5173/api/v1/conversations/PEA?limit=10&offset=0"
```

---

### 2. Add Single Message
**POST** `/{portfolio_name}/message`

Add a single message to conversation history.

**Request Body:**
```json
{
  "source": "user",
  "content": "Message content here"
}
```

**Response:** Updated conversation history (same as GET endpoint)

**Example:**
```bash
curl -X POST "http://localhost:5173/api/v1/conversations/PEA/message" \
  -H "Content-Type: application/json" \
  -d '{"source": "user", "content": "Buy AAPL"}'
```

---

### 3. Add Multiple Messages (Bulk)
**POST** `/{portfolio_name}/messages/bulk`

Add multiple messages in a single request (batch import/sync).

**Request Body:**
```json
{
  "messages": [
    {"source": "user", "content": "First message"},
    {"source": "chatbot", "content": "Second message"}
  ]
}
```

**Response:** Updated conversation history

**Example:**
```bash
curl -X POST "http://localhost:5173/api/v1/conversations/PEA/messages/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"source": "user", "content": "Buy AAPL"},
      {"source": "alert", "content": "Price alert triggered"}
    ]
  }'
```

---

### 4. Get Message Count
**GET** `/{portfolio_name}/count`

Get total message count, optionally by source.

**Query Parameters:**
- `source` (string, optional): Filter by source

**Response (without source filter):**
```json
{
  "portfolio_name": "PEA",
  "count": 25,
  "by_source": {
    "user": 10,
    "chatbot": 8,
    "alert": 5,
    "notification": 2
  }
}
```

**Response (with source filter):**
```json
{
  "portfolio_name": "PEA",
  "count": 10
}
```

**Example:**
```bash
curl "http://localhost:5173/api/v1/conversations/PEA/count"
curl "http://localhost:5173/api/v1/conversations/PEA/count?source=user"
```

---

### 5. Get Conversation Statistics
**GET** `/{portfolio_name}/stats`

Get comprehensive conversation statistics.

**Response:**
```json
{
  "portfolio_name": "PEA",
  "total_messages": 25,
  "messages_by_source": {
    "user": 10,
    "chatbot": 8,
    "alert": 5,
    "notification": 2
  },
  "first_message": {
    "source": "user",
    "content": "Portfolio created",
    "datetime": "2026-01-01T09:00:00"
  },
  "last_message": {
    "source": "alert",
    "content": "Stop loss triggered",
    "datetime": "2026-05-26T14:30:00"
  }
}
```

**Example:**
```bash
curl "http://localhost:5173/api/v1/conversations/PEA/stats"
```

---

### 6. Get Last Message
**GET** `/{portfolio_name}/last`

Get the most recent message.

**Query Parameters:**
- `source` (string, optional): Filter by source

**Response:**
```json
{
  "portfolio_name": "PEA",
  "message": {
    "source": "alert",
    "content": "Stop loss triggered",
    "datetime": "2026-05-26T14:30:00"
  }
}
```

**Example:**
```bash
curl "http://localhost:5173/api/v1/conversations/PEA/last"
curl "http://localhost:5173/api/v1/conversations/PEA/last?source=user"
```

---

### 7. Get Messages by Source
**GET** `/{portfolio_name}/by-source/{source}`

Get all messages from a specific source.

**Path Parameters:**
- `source` (string): Message source (user|chatbot|alert|notification)

**Query Parameters:**
- `limit` (integer, optional): Max messages to return

**Response:** Conversation history with filtered messages

**Example:**
```bash
curl "http://localhost:5173/api/v1/conversations/PEA/by-source/user"
curl "http://localhost:5173/api/v1/conversations/PEA/by-source/alert?limit=20"
```

---

### 8. Search Messages
**GET** `/{portfolio_name}/search`

Search messages by content (case-insensitive).

**Query Parameters:**
- `q` (string, required): Search query
- `source` (string, optional): Filter by source

**Response:** Filtered conversation history

**Example:**
```bash
curl "http://localhost:5173/api/v1/conversations/PEA/search?q=AAPL"
curl "http://localhost:5173/api/v1/conversations/PEA/search?q=price&source=alert"
```

---

### 9. Export Conversation
**GET** `/{portfolio_name}/export`

Export conversation history in JSON or CSV format.

**Query Parameters:**
- `format` (string, optional): Export format (json|csv, default: json)

**Response (JSON):**
```json
{
  "portfolio_name": "PEA",
  "format": "json",
  "count": 2,
  "data": [
    {"source": "user", "content": "Buy AAPL", "datetime": "2026-05-26T14:00:00"},
    {"source": "alert", "content": "Price alert", "datetime": "2026-05-26T14:30:00"}
  ]
}
```

**Response (CSV):**
```json
{
  "portfolio_name": "PEA",
  "format": "csv",
  "count": 2,
  "data": "source,content,datetime\nuser,Buy AAPL,2026-05-26T14:00:00\nalert,Price alert,2026-05-26T14:30:00\n"
}
```

**Example:**
```bash
curl "http://localhost:5173/api/v1/conversations/PEA/export?format=json"
curl "http://localhost:5173/api/v1/conversations/PEA/export?format=csv"
```

---

### 10. Clear All Messages
**DELETE** `/{portfolio_name}`

Clear all conversation history for a portfolio. ⚠️ **Permanent operation**

**Response:**
```json
{
  "status": "cleared",
  "portfolio_name": "PEA",
  "details": {
    "message": "All conversation history has been deleted"
  }
}
```

**Example:**
```bash
curl -X DELETE "http://localhost:5173/api/v1/conversations/PEA"
```

---

### 11. Clear Messages by Source
**DELETE** `/{portfolio_name}/by-source/{source}`

Clear all messages from a specific source.

**Path Parameters:**
- `source` (string): Message source (user|chatbot|alert|notification)

**Response:**
```json
{
  "status": "cleared",
  "portfolio_name": "PEA",
  "details": {
    "source": "alert",
    "cleared_count": 5,
    "remaining_count": 20
  }
}
```

**Example:**
```bash
curl -X DELETE "http://localhost:5173/api/v1/conversations/PEA/by-source/alert"
```

---

## Message Sources

Messages are categorized by source:

| Source | Use Case |
|--------|----------|
| `user` | User-initiated messages, commands |
| `chatbot` | AI assistant responses |
| `alert` | Price alerts, triggered conditions |
| `notification` | System notifications, events |

---

## Storage

- **Location:** `~/.cresus/db/portfolios/{portfolio_name}/conversations/history.json`
- **Format:** JSON array of message objects
- **Persistence:** Automatically persisted to disk after each operation
- **Structure:**
```json
[
  {
    "source": "user",
    "content": "Message text",
    "datetime": "2026-05-26T14:30:00"
  }
]
```

---

## Error Handling

All endpoints return standard HTTP status codes:

- **200 OK** - Successful retrieval
- **201 Created** - Successful creation
- **204 No Content** - Successful deletion
- **400 Bad Request** - Invalid parameters
- **404 Not Found** - Portfolio or resource not found
- **500 Internal Server Error** - Server error

Error responses:
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Usage Examples

### Example 1: Get Recent User Messages
```bash
curl "http://localhost:5173/api/v1/conversations/PEA/by-source/user?limit=10"
```

### Example 2: Search for Price Alerts
```bash
curl "http://localhost:5173/api/v1/conversations/PEA/search?q=price&source=alert"
```

### Example 3: Get Conversation Summary
```bash
curl "http://localhost:5173/api/v1/conversations/PEA/stats"
```

### Example 4: Log Multiple Events
```bash
curl -X POST "http://localhost:5173/api/v1/conversations/PEA/messages/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"source": "alert", "content": "Entry signal triggered"},
      {"source": "notification", "content": "Order executed"},
      {"source": "chatbot", "content": "Position opened at €150.25"}
    ]
  }'
```

### Example 5: Export and Backup
```bash
curl "http://localhost:5173/api/v1/conversations/PEA/export?format=json" > backup.json
```

---

## Related

- **Frontend Component:** `/src/components/portfolio/ConversationPanel.tsx`
- **Backend Class:** `/src/tools/conversation.py` (ConversationManager)
- **API Route File:** `/src/api/routes/conversations.py`

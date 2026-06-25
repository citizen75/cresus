# API Server Restart Guide

## Problem
The Conversation API endpoints were added but the API server is running the old code without these routes.

## Solution

### 1. Stop the API Server
```bash
# If running with Ctrl+C
Ctrl+C

# Or if running in background:
pkill -f "uvicorn"
pkill -f "cresus-api"
```

### 2. Verify Routes are Registered
```bash
python << 'EOF'
import sys
from pathlib import Path
sys.path.insert(0, '/Volumes/Data/dev/cresus/src')
from api.app import create_app
app = create_app()
conversations_routes = [r for r in app.routes if hasattr(r, 'path') and 'conversations' in r.path]
print(f"✓ Found {len(conversations_routes)} conversation routes")
EOF
```

### 3. Start the API Server

**Option A: Using installed entry point**
```bash
cresus-api
```

**Option B: Direct uvicorn**
```bash
cd /Volumes/Data/dev/cresus
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Option C: Using the API main module**
```bash
cd /Volumes/Data/dev/cresus
python -m src.api.main
```

### 4. Verify Server is Running
```bash
curl http://localhost:8000/api/v1/health
# Should return: {"status":"ok"}
```

### 5. Test Conversation Endpoint
```bash
curl -X POST http://localhost:8000/api/v1/conversations/test_portfolio/message \
  -H "Content-Type: application/json" \
  -d '{"source":"user","content":"Test message"}'
# Should return: {"portfolio_name":"test_portfolio","history":[...],"count":1}
```

### 6. Verify Frontend Can Reach API

Check the browser console (F12) when on the portfolio page:
1. The send button should trigger API calls
2. You should see logs like:
   - `[ConversationPanel] Sending message to: /api/v1/conversations/PEA/message`
   - `[ConversationPanel] Response status: 200`

## Common Issues

**Issue: 404 Error persists after restart**
- The API server might still be running the old code
- Check all Python processes: `ps aux | grep python`
- Kill all: `pkill -f python`
- Restart fresh

**Issue: Connection refused**
- API server not running
- Running on wrong port (check URL in error)
- Use port 8000: `--port 8000`

**Issue: ConversationManager import error**
- Ensure `/Volumes/Data/dev/cresus/src/tools/conversation.py` exists
- Verify `src/tools/__init__.py` exists

## Endpoints Available

Once server is restarted and running, these endpoints are available:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/conversations/{portfolio}/message` | Add message |
| GET | `/api/v1/conversations/{portfolio}` | Get history |
| GET | `/api/v1/conversations/{portfolio}/count` | Get count |
| GET | `/api/v1/conversations/{portfolio}/stats` | Get statistics |
| POST | `/api/v1/conversations/{portfolio}/messages/bulk` | Bulk add |
| DELETE | `/api/v1/conversations/{portfolio}` | Clear all |

All endpoints return 200 OK with data, or 500 with error details.

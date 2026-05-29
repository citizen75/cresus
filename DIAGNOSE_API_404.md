# Diagnosing 404 "Not Found" Error for Conversation API

## Quick Diagnosis Checklist

### 1. **API Server Status**
```bash
# Check if API is running on port 8000
lsof -i :8000

# Or try to connect
curl -v http://localhost:8000/api/v1/health
```

**Expected response:**
```json
{"status":"ok"}
```

**If you get "Connection refused":**
→ API server is not running, start it first

### 2. **Check Vite Proxy Configuration**
The frontend is running at: `http://192.168.0.130:5173`
The API should be at: `http://localhost:8000`

Vite is configured to proxy `/api/*` requests to the API server.

**Check if proxy is working:**
```bash
# While frontend dev server is running
curl -v http://192.168.0.130:5173/api/v1/health
```

### 3. **Verify Conversation Routes Exist**
```bash
python << 'EOF'
import sys
sys.path.insert(0, '/Volumes/Data/dev/cresus/src')
from api.app import create_app
app = create_app()
routes = [r for r in app.routes if hasattr(r, 'path') and 'conversations' in r.path]
print(f"Conversation routes registered: {len(routes)}")
for r in routes:
    print(f"  {r.methods if hasattr(r, 'methods') else 'N/A'} {r.path}")
EOF
```

### 4. **Test Endpoint Directly with curl**
```bash
# Test POST /conversations/{portfolio}/message
curl -X POST http://localhost:8000/api/v1/conversations/PEA/message \
  -H "Content-Type: application/json" \
  -d '{"source":"user","content":"Test"}'

# Should return 200 with data, not 404
```

## Common Causes and Solutions

### **Cause 1: API Server Not Running**
**Symptom:** curl shows "Connection refused"

**Solution:**
```bash
cd /Volumes/Data/dev/cresus
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### **Cause 2: Old API Server Still Running**
**Symptom:** Routes don't appear even after restart

**Solution:**
```bash
# Kill all Python processes
pkill -f uvicorn
pkill -f "python.*api"

# Wait 2 seconds
sleep 2

# Restart API
cd /Volumes/Data/dev/cresus
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### **Cause 3: Frontend Dev Server Proxy Not Working**
**Symptom:** Endpoint works with localhost but not with 192.168.0.130

**Solution:**
```bash
# Restart frontend dev server
cd /Volumes/Data/dev/cresus/front
npm run dev
```

The dev server will show:
```
╔════════════════════════════════════════╗
║     Cresus Frontend Configuration      ║
╠════════════════════════════════════════╣
║ Frontend: http://0.0.0.0:5173
║ API Host: localhost
║ API Port: 8000
║ API URL:  http://localhost:8000
╚════════════════════════════════════════╝
```

### **Cause 4: Network/Firewall Blocking API**
**Symptom:** API works locally but not from other machines

**Solution:**
Make sure API is listening on all interfaces:
```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Then test from another machine:
```bash
curl http://192.168.0.130:8000/api/v1/health
```

## Step-by-Step Fix

1. **Kill all running processes:**
   ```bash
   pkill -f uvicorn
   pkill -f "npm.*dev"
   ```

2. **Start API server:**
   ```bash
   cd /Volumes/Data/dev/cresus
   python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **In another terminal, start frontend:**
   ```bash
   cd /Volumes/Data/dev/cresus/front
   npm run dev
   ```

4. **Test the conversation endpoint:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/conversations/PEA/message \
     -H "Content-Type: application/json" \
     -d '{"source":"user","content":"Test"}'
   ```

5. **Open browser and test:**
   - Go to: `http://localhost:5173/portfolios/PEA`
   - Click send in the Conversations panel
   - Check browser console (F12) for logs

## Browser Console Debugging

When you click "Send" in the Conversations panel, you should see in console:
```
[ConversationPanel] Sending message to: /api/v1/conversations/PEA/message
[ConversationPanel] Portfolio: PEA
[ConversationPanel] Response status: 200
[ConversationPanel] Response data: {portfolio_name: 'PEA', history: Array(1), count: 1}
```

**If you see 404:**
```
[ConversationPanel] Response status: 404
[ConversationPanel] API Error: 404 {"detail":"Not Found"}
```

This means the API endpoint doesn't exist on the running server. Restart the API.

## Files to Check

1. **API route file exists:**
   ```bash
   ls -la /Volumes/Data/dev/cresus/src/api/routes/conversations.py
   ```

2. **Route is imported in app.py:**
   ```bash
   grep "conversations" /Volumes/Data/dev/cresus/src/api/app.py
   ```

3. **ConversationManager exists:**
   ```bash
   ls -la /Volumes/Data/dev/cresus/src/tools/conversation.py
   ```

## Final Test

Once everything is running:
```bash
# Terminal 1 - API Server
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd front && npm run dev

# Terminal 3 - Test API
curl -X POST http://localhost:8000/api/v1/conversations/test/message \
  -H "Content-Type: application/json" \
  -d '{"source":"user","content":"Hello"}'
```

Expected response:
```json
{
  "portfolio_name": "test",
  "history": [
    {
      "source": "user",
      "content": "Hello",
      "datetime": "2026-05-26T15:00:00"
    }
  ],
  "count": 1
}
```

If you still see 404, provide:
1. Output of `curl -v http://localhost:8000/api/v1/conversations/test/message` 
2. API server logs
3. Browser console logs

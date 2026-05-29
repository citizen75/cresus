#!/bin/bash
# Quick verification script for Conversation API setup

echo "╔════════════════════════════════════════╗"
echo "║  Conversation API Setup Verification   ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check 1: Files exist
echo "📋 Checking files..."
files=(
    "/Volumes/Data/dev/cresus/src/api/routes/conversations.py"
    "/Volumes/Data/dev/cresus/src/tools/conversation.py"
    "/Volumes/Data/dev/cresus/src/api/app.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file (MISSING)"
    fi
done

# Check 2: API Server Status
echo ""
echo "🔍 Checking API Server..."
if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} API server running on localhost:8000"

    # Check if conversation routes are available
    response=$(curl -s -X GET http://localhost:8000/api/v1/conversations/test_check/count)
    if echo "$response" | grep -q "test_check"; then
        echo -e "  ${GREEN}✓${NC} Conversation routes are registered"
    else
        echo -e "  ${YELLOW}⚠${NC} Conversation routes may not be registered. Response: $response"
    fi
else
    echo -e "  ${RED}✗${NC} API server NOT running on localhost:8000"
    echo "      Start it with: python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
fi

# Check 3: Frontend Dev Server
echo ""
echo "🌐 Checking Frontend..."
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Frontend dev server running on localhost:5173"
else
    if curl -s http://192.168.0.130:5173 > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Frontend dev server running on 192.168.0.130:5173"
    else
        echo -e "  ${YELLOW}⚠${NC} Frontend may not be running"
        echo "      Start it with: cd front && npm run dev"
    fi
fi

# Check 4: Test Conversation Endpoint
echo ""
echo "🧪 Testing Conversation Endpoint..."
response=$(curl -s -X POST http://localhost:8000/api/v1/conversations/verify_test/message \
    -H "Content-Type: application/json" \
    -d '{"source":"user","content":"Test message"}')

if echo "$response" | grep -q "verify_test"; then
    echo -e "  ${GREEN}✓${NC} Conversation endpoint working"
    echo "      Response: $(echo $response | head -c 100)..."
else
    echo -e "  ${RED}✗${NC} Conversation endpoint not working"
    echo "      Response: $response"
fi

# Check 5: Python dependencies
echo ""
echo "📦 Checking Python dependencies..."
python3 -c "from tools.conversation import ConversationManager; print('  \033[0;32m✓\033[0m ConversationManager imports')" 2>/dev/null || echo -e "  ${RED}✗${NC} ConversationManager not available"
python3 -c "from api.routes.conversations import router; print('  \033[0;32m✓\033[0m Conversation routes import')" 2>/dev/null || echo -e "  ${RED}✗${NC} Conversation routes not available"

# Summary
echo ""
echo "╔════════════════════════════════════════╗"
echo "║             Summary                    ║"
echo "╚════════════════════════════════════════╝"
echo "If all checks pass, the setup is correct."
echo "If API server check fails, restart it:"
echo "  cd /Volumes/Data/dev/cresus"
echo "  python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload"

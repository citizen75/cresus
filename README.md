# Cresus — Portfolio Management Application

A modern portfolio management system with FastAPI backend, MCP server for AI assistants, and React frontend.

## Quick Start

### 1. Install dependencies

```bash
cd /Volumes/Data/dev/cresus
pip install -e .
npm install --prefix front
```

### 2. Start services

**Option A: Using the CLI (recommended)**
```bash
python src/cli/main.py
# cresus> service start all -d
# cresus> status
```

**Option B: Start services individually**
```bash
# Terminal 1: API
python src/api/main.py

# Terminal 2: Frontend
cd front && npm run dev

# Terminal 3: MCP (optional, for Claude Desktop)
python src/mcp/main.py
```

### 3. Access the app

- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

## Architecture

```
cresus/
├── src/
│   ├── portfolio/        # Shared domain layer (manager, metrics, journal)
│   ├── api/              # FastAPI backend
│   ├── mcp/              # MCP server for AI assistants
│   └── cli/              # cmd2 service manager
├── front/                # React + TypeScript SPA
├── config/               # YAML configs
├── db/local/             # Data storage (portfolios, cache, history)
└── logs/                 # Service logs
```

## CLI Commands

```bash
service start api               # Start API server
service start front             # Start frontend (Vite)
service start mcp               # Start MCP server
service start all -d            # Start all services as daemons
service status                  # Check service status
service stop api                # Stop API server
service logs api 20             # Show last 20 lines of API logs
```

## Features (MVP)

- ✅ Portfolio management (create, list, view)
- ✅ Position tracking (buy/sell transactions)
- ✅ Performance metrics (Sharpe ratio, Sortino, max drawdown)
- ✅ Portfolio value history
- ✅ API endpoints for all functionality
- ✅ MCP tools for Claude Desktop integration
- ✅ CLI service manager
- ✅ React frontend with portfolio dashboard

## API Endpoints

```
GET    /api/v1/health                    # Health check
GET    /api/v1/portfolios                # List portfolios
POST   /api/v1/portfolios                # Create portfolio
GET    /api/v1/portfolios/{name}         # Get portfolio details
GET    /api/v1/portfolios/{name}/value   # Get current value
GET    /api/v1/portfolios/{name}/metrics # Get metrics
GET    /api/v1/portfolios/{name}/history # Get value history
```

## MCP Tools (Claude Desktop)

Add to `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cresus": {
      "command": "python",
      "args": ["/Volumes/Data/dev/cresus/src/mcp/main.py"],
      "env": {
        "CRESUS_PROJECT_ROOT": "/Volumes/Data/dev/cresus"
      }
    }
  }
}
```

Then use Claude to:
- List all portfolios
- Check portfolio values and performance
- View open positions
- Get historical analytics

## Development

### Add a new portfolio

Edit `config/portfolios.yml`:
```yaml
portfolios:
  - name: my_portfolio
    type: paper
    currency: EUR
    initial_capital: 100000
```

### Record a transaction

```bash
curl -X POST http://localhost:8000/api/v1/portfolios/main/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "BUY",
    "ticker": "AAPL",
    "quantity": 10,
    "price": 150.0,
    "fees": 10.0
  }'
```

## Next Steps

- [ ] Full PortfolioManager with real position tracking
- [ ] Google Sheets synchronization
- [ ] Historical performance analytics
- [ ] Real broker integration (Interactive Brokers)
- [ ] Trading alerts and notifications
- [ ] Advanced charting (candlestick, technical indicators)
- [ ] Portfolio rebalancing recommendations
- [ ] Risk metrics (VAR, CVaR, Kelly criterion)

## License

MIT

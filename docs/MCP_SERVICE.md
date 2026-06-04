# Cresus MCP Service

Cresus provides an independent Model Context Protocol (MCP) server that exposes portfolio management tools to Hermes and other MCP clients.

## Architecture

```
┌─────────────────┐
│   Hermes Agent  │
└────────┬────────┘
         │ (MCP Client)
         │
┌────────▼────────────────────┐
│  Cresus MCP Server          │
│  (Stdio Transport)          │
│  - 16 Portfolio Tools       │
│  - Automatic Discovery      │
│  - Real-time Data Access    │
└────────┬────────────────────┘
         │
┌────────▼────────────────────┐
│  Cresus REST API            │
│  (http://192.168.0.130:6501)│
│  - Portfolio Management      │
│  - Real-time Quotes         │
│  - Trade History            │
└─────────────────────────────┘
```

## Service Management

### Check Status
```bash
cresus-mcp-server status
```

Output shows:
- Configuration status
- Tool availability
- Log location
- Quick start commands

### Available Commands
```bash
cresus-mcp-server start   # Register MCP service
cresus-mcp-server stop    # Deregister service
cresus-mcp-server status  # Show service status
```

## Integration with Hermes

The MCP server integrates automatically with Hermes for portfolio queries.

### Test Connection
```bash
hermes mcp test cresus
```

Expected output:
- ✓ Connected (connection time)
- ✓ Tools discovered: 16
- Tool list

### Use in Hermes
```bash
# List all MCP servers
hermes mcp list

# Explicitly request portfolio data
hermes "Please run: curl -s http://192.168.0.130:6501/api/v1/portfolios/PEA | jq '.positions[]'"
```

## Available Tools (16 Total)

### Portfolio Queries
- `list_portfolios()` - List all portfolios
- `get_portfolio(name)` - Get portfolio details
- `get_portfolio_positions(portfolio_name)` - Get holdings
- `get_portfolio_performance(portfolio_name)` - Get returns
- `get_portfolio_metrics(portfolio_name)` - Get Sharpe, drawdown, etc
- `get_portfolio_allocation(portfolio_name)` - Get asset allocation
- `get_portfolio_value(portfolio_name)` - Get total value
- `get_portfolio_risk(portfolio_name)` - Get risk metrics
- `get_portfolio_transactions(portfolio_name)` - Get trade history

### Portfolio Management
- `create_portfolio(name, type, currency)` - Create new portfolio
- `update_portfolio(name, config)` - Update configuration
- `delete_portfolio(name)` - Delete portfolio
- `add_position(portfolio_name, ticker, quantity, entry_price)` - Add position
- `close_position(portfolio_name, position_id)` - Close position
- `compare_portfolios(names)` - Compare portfolios
- `rebalance_portfolio(portfolio_name, target_allocation)` - Rebalance

## Configuration

### Hermes Config
Location: `~/.hermes/config.yaml`

```yaml
mcp_servers:
  cresus:
    name: Cresus Portfolio API
    type: stdio
    command: /Volumes/Data/dev/cresus/venv/bin/python
    args:
      - -m
      - cresus_mcp.main
    cwd: /Volumes/Data/dev/cresus
    env:
      CRESUS_API_URL: http://192.168.0.130:6501/api/v1
      CRESUS_LOG_LEVEL: INFO
    enabled: true
    auto_start: true
```

### Environment Variables
- `CRESUS_API_URL` - Backend API URL (default: http://192.168.0.130:6501/api/v1)
- `CRESUS_LOG_LEVEL` - Log level (DEBUG, INFO, WARNING, ERROR)

## Logging

MCP server logs are written to: `logs/mcp.log`

View recent logs:
```bash
tail -f logs/mcp.log
```

## Troubleshooting

### MCP connection fails
```bash
# Reinitialize Hermes
hermes postinstall

# Check Hermes MCP status
hermes mcp list
```

### Tools not discovered
```bash
# Test connection with debug output
hermes mcp test cresus
```

### API connection fails
Check that Cresus API is running:
```bash
curl http://192.168.0.130:6501/api/v1/portfolios
```

## Performance

- **Connection time**: ~320ms (one-time on first use)
- **Tool discovery**: ~50ms
- **Query latency**: 50-200ms depending on portfolio complexity
- **Caching**: None (live queries)

## Security

- **Authentication**: None required (local network)
- **Transport**: Stdio (subprocess, no network exposure)
- **API Key**: Optional bearer token support
- **TLS**: Not supported for stdio transport

## Implementation Details

### Entry Points
```bash
# Direct MCP server
python -m cresus_mcp.main

# Service manager
cresus-mcp-server status
cresus-mcp-server start
cresus-mcp-server stop
```

### Source Files
- MCP Server: `src/cresus_mcp/server.py`
- Service Manager: `src/cresus_mcp/service.py`
- Portfolio Domain: `src/cresus_mcp/domains.py`
- Entry Point: `src/cresus_mcp/main.py`

### Dependencies
- `mcp>=1.0.0` - Model Context Protocol
- `httpx>=0.20.0` - Async HTTP client
- `loguru>=0.7.0` - Logging

## Related

- [Hermes Integration](../docs/HERMES.md)
- [Portfolio Management](../docs/PORTFOLIO.md)
- [REST API](../docs/API.md)

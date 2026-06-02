# Hermes Agent Integration with Cresus

Hermes is an autonomous agent framework for AI-driven portfolio management. This integration allows Hermes to control and analyze Cresus portfolios using the MCP (Model Context Protocol) interface.

## Quick Start

### For Existing Hermes Installation (Manual Setup)

**Edit `~/.hermes/config.yaml`** and add this section:

```yaml
mcp_servers:
  cresus:
    name: "Cresus Portfolio API"
    type: "stdio"
    command: "python"
    args: ["-m", "src.mcp.main"]
    env:
      CRESUS_API_URL: "http://localhost:8000/api/v1"
      CRESUS_LOG_LEVEL: "INFO"
    enabled: true
    auto_start: true

skills:
  enabled:
    - "portfolio_manager"
    - "screener_analyzer"
    - "performance_analyzer"
    # ... your existing skills
```

Then copy the skill folders:
```bash
cp -r init/hermes/skills/portfolio_manager ~/.hermes/skills/
cp -r init/hermes/skills/screener_analyzer ~/.hermes/skills/
cp -r init/hermes/skills/performance_analyzer ~/.hermes/skills/
```

### Or Use Automated Setup (Fresh Install)

```bash
cresus init --hermes
```

This will:
- Create `~/.hermes/` directory structure  
- Copy all Hermes configuration files
- Setup Hermes skills for portfolio management
- Configure the Cresus MCP server

### Start the Services

```bash
# Start Cresus API
cresus service start api

# Launch Hermes Agent
hermes run
```

## Configuration

### Main Configuration File: `~/.hermes/config.yaml`

This is the main Hermes configuration file. The Cresus integration adds:
- Agent personality and role
- MCP server configuration
- Available skills
- Safety constraints
- Logging settings

### Skills

Three main skills are included:

#### 1. **portfolio_manager** (`skills/portfolio_manager.yml`)
- Create and manage portfolios
- Analyze portfolio performance
- View positions and allocation
- Compare multiple portfolios
- Rebalance portfolios

**Example interactions:**
```
"Create a portfolio called 'Growth' with 50000€"
"Analyze my Main portfolio"
"Compare Main and Secondary portfolios"
"Rebalance portfolio to 60% stocks, 40% bonds"
```

#### 2. **screener_analyzer** (`skills/screener_analyzer.yml`)
- Create stock screeners
- Test screener formulas
- Run screeners to find matching stocks
- Validate DSL formulas

**Example interactions:**
```
"Create a screener for momentum stocks with SHA and RSI"
"Test the formula: sha_14_green and rsi_14 > 50"
"Run the momentum screener"
"Show results from the CAC40 momentum screener"
```

#### 3. **performance_analyzer** (`skills/performance_analyzer.yml`)
- Analyze portfolio metrics
- Track performance history
- Compare strategies
- Generate performance reports

**Example interactions:**
```
"What's my Main portfolio's Sharpe ratio?"
"Show me the transaction history for Secondary"
"Analyze performance of the last 3 months"
"Compare performance across all my portfolios"
```

## Architecture

### Data Flow

```
User Input
    ↓
Hermes Agent (understanding & planning)
    ↓
Skills (route to appropriate tool)
    ↓
MCP Client (format request)
    ↓
Cresus MCP Server (stdio)
    ↓
API Calls (http://localhost:8000/api/v1)
    ↓
Cresus Backend (business logic)
    ↓
Response → Agent → User
```

### Skills Hierarchy

```
Hermes Agent
├── portfolio_manager (16 operations)
├── screener_analyzer (9 operations)
├── performance_analyzer (6 operations)
└── strategy_executor (8 operations)
```

## Available Tools

### Portfolio Operations (16)
- `list_portfolios` - List all portfolios
- `create_portfolio` - Create new portfolio
- `get_portfolio` - Get portfolio details
- `update_portfolio` - Update configuration
- `delete_portfolio` - Delete portfolio
- `get_portfolio_positions` - View current positions
- `get_portfolio_metrics` - Get performance metrics
- `get_portfolio_performance` - Get performance data
- `get_portfolio_transactions` - View transaction history
- `get_portfolio_value` - Get current value
- `get_portfolio_allocation` - Get asset allocation
- `get_portfolio_risk` - Get risk metrics
- `add_position` - Add manual position
- `close_position` - Close position
- `compare_portfolios` - Compare multiple portfolios
- `rebalance_portfolio` - Rebalance to target allocation

### Screener Operations (9)
- `list_screeners` - List screeners
- `get_screener` - Get screener details
- `create_screener` - Create new screener
- `update_screener` - Update screener
- `delete_screener` - Delete screener
- `run_screener` - Execute screener
- `validate_formula` - Test formula
- `get_results` - Get screener results

### Performance Analysis (6)
- `get_metrics` - Portfolio metrics
- `get_performance` - Performance history
- `get_transactions` - Transaction log
- Plus analytics capabilities

## Safety Features

Hermes includes built-in safety constraints:

```yaml
constraints:
  max_portfolio_size: 50          # Max number of positions
  min_position_size: 100€         # Minimum position size
  max_daily_trades: 20            # Max trades per day
  require_confirmation_for:
    - "large_trades"              # > 10000€
    - "new_portfolios"
    - "strategy_changes"
```

**Confirmation Required For:**
- Large trades (> 10,000€)
- Creating new portfolios
- Changing strategies
- Major rebalancing

## Environment Variables

Located in `~/.hermes/.env`:

```bash
# API Configuration
CRESUS_API_URL=http://localhost:8000/api/v1
CRESUS_API_KEY=

# Agent Configuration
HERMES_MODEL=gpt-4
HERMES_TEMPERATURE=0.7
HERMES_MAX_TOKENS=2000

# Safety
HERMES_REQUIRE_CONFIRMATION=true
HERMES_DAILY_LOSS_LIMIT=-0.05
```

## Troubleshooting

### "MCP Server not responding"
```bash
# Check if API is running
curl http://localhost:8000/api/v1/health

# Start API
cresus service start api

# Test MCP
python -m src.mcp.main
```

### "Portfolio not found"
```bash
# List available portfolios
hermes "list my portfolios"

# Create missing portfolio
hermes "create a portfolio called 'Main' with 100000€"
```

### "Formula validation error"
```bash
# Check available indicators
hermes "what indicators are available?"

# Validate formula step by step
hermes "test formula: sha_14_green and rsi_14"
```

### Logs

Check logs at:
```
~/.hermes/logs/hermes.log
~/.hermes/logs/cresus_agent.log
```

## Examples

### Portfolio Analysis Workflow

```
User: "Analyze my performance"

Hermes:
1. Lists all portfolios
2. Gets metrics for each
3. Generates comprehensive report
4. Alerts on risk issues
5. Suggests optimizations
```

### Screener Workflow

```
User: "Find momentum stocks in CAC40"

Hermes:
1. Creates screener with momentum formula
2. Validates formula on sample data
3. Runs screener on CAC40
4. Shows results with top matches
5. Suggests adding to watchlist
```

### Optimization Workflow

```
User: "Optimize my Main portfolio"

Hermes:
1. Analyzes current allocation
2. Identifies concentration risks
3. Suggests diversification
4. Proposes rebalancing
5. Executes rebalancing with confirmation
```

## Integration with Cresus APIs

The MCP integration provides access to:

### REST APIs (via MCP)
- `/portfolios` - Portfolio management
- `/screener` - Screener operations
- `/strategies` - Strategy management
- `/backtests` - Backtest analysis
- `/watchlist` - Watchlist management
- `/data` - Market data

### Real-time Data
- Portfolio positions and values
- Transaction history
- Performance metrics
- Market indicators
- Strategy signals

## Advanced Configuration

### Custom Prompts

Edit `~/.hermes/config/system_prompt.md` to customize agent behavior

### Custom Skills

Add new skills in `~/.hermes/skills/`:

```yaml
skill_name: "my_skill"
description: "What this skill does"
triggers: ["trigger_words"]
actions:
  - name: "action_name"
    mcp_tool: "cresus_mcp_tool"
    parameters: [...]
```

### Extended Capabilities

Extend agent with additional MCP servers:

```yaml
mcp_servers:
  cresus:
    # ... existing config
  other_service:
    command: "python -m other_service.mcp"
```

## Performance Tips

1. **Cache Results**: Hermes caches API responses automatically
2. **Batch Operations**: Combine multiple requests when possible
3. **Limit Data**: Use `limit` parameters for large result sets
4. **Monitor Resources**: Check `~/.hermes/logs/` for performance issues

## Support

For issues or questions:
1. Check logs in `~/.hermes/logs/`
2. Verify Cresus API is running
3. Test MCP server directly: `python -m src.mcp.main`
4. Review configuration in `~/.hermes/config/`

## Further Reading

- [MCP Protocol](https://modelcontextprotocol.io/)
- [Cresus MCP Implementation](/src/mcp/README.md)
- [Portfolio Management Guide](/docs/portfolio.md)
- [Screener DSL Guide](/docs/screener.md)

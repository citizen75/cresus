# Hermes Integration with Cresus

Hermes is an autonomous agent framework that queries and analyzes Cresus portfolios using pre-configured CLI-based skills.

## Key Features

✅ **Direct CLI Integration** - Uses `cresus-mcp` CLI wrapper for reliable execution  
✅ **Pre-configured Skills** - Three Cresus skills ready to use  
✅ **Simple Setup** - No complex MCP server configuration needed  
✅ **Large Context Window** - Supports 32K+ tokens for comprehensive analysis  
✅ **Automatic Skill Loading** - Skills enabled by default  

## Quick Start

### Setup

1. **Copy skills to Hermes:**
   ```bash
   mkdir -p ~/.hermes/skills/cresus
   cp -r init/hermes/skills/* ~/.hermes/skills/cresus/
   ```

2. **Update Hermes configuration:**
   ```bash
   # Copy config file
   cp init/hermes/config.yaml ~/.hermes/config.yaml
   
   # Update system prompt
   mkdir -p ~/.hermes/config
   cp init/hermes/config/system_prompt.md ~/.hermes/config/system_prompt.md
   ```

3. **Verify Ollama context window (Important!):**
   ```bash
   # Check current setting
   sudo systemctl show ollama | grep OLLAMA_NUM_CTX
   
   # If not 32768+, edit systemd service:
   sudo systemctl edit ollama
   
   # Add to [Service] section:
   Environment="OLLAMA_NUM_CTX=32768"
   
   # Reload and restart
   sudo systemctl daemon-reload
   sudo systemctl restart ollama
   ```

### Start Using

```bash
# List portfolios
hermes -q "list my portfolios"

# Show positions
hermes -q "show positions in PEA"

# Get metrics
hermes -q "what are PEA metrics?"
```

## Available Skills

### 1. Portfolio Manager (`cresus/portfolio_manager`)

Query and analyze Cresus portfolios via `cresus-mcp` CLI.

**Available Commands:**
```bash
cresus-mcp portfolio list                    # List all portfolios
cresus-mcp portfolio positions <name>        # Get positions
cresus-mcp portfolio metrics <name>          # Get metrics
cresus-mcp portfolio performance <name>      # Get performance
cresus-mcp portfolio allocation <name>       # Get allocation
cresus-mcp portfolio value <name>            # Get value
```

**Portfolios:**
- PEA (French tax-advantaged account, real)
- BNP (BNP Paribas, real)
- test (Test portfolio)
- _global (Global paper portfolio)
- etf_pea_trend, cac_trend, nasdaq_100_trend (Strategy portfolios)

### 2. Screener Analyzer (`cresus/screener_analyzer`)

Create and test stock screeners using DSL formulas.

**Available Actions:**
- `list_screeners` - List all screeners
- `create_screener` - Create new screener with formula
- `validate_formula` - Test formula syntax
- `run_screener` - Execute screener
- `get_results` - Get screener results

### 3. Performance Analyzer (`cresus/performance_analyzer`)

Analyze and compare portfolio performance.

**Available Tools:**
- `cresus_performance_summary` - Get portfolio metrics
- `cresus_performance_compare` - Compare two portfolios

## Configuration Files

### `config.yaml`

Main Hermes configuration with:
- Model settings (Ollama at 192.168.0.160:11434)
- Context window configuration (32768 minimum)
- Skill definitions
- Agent settings

### `config/system_prompt.md`

Instructions for the Hermes agent:
- Focus on using `cresus-mcp` CLI commands
- Return API data as-is without enrichment
- Portfolio data includes company names (from API)

### `skills/portfolio_manager/skill.yml`

Portfolio manager skill definition with actions mapping to `cresus-mcp` commands.

### `skills/screener_analyzer/skill.yml`

Screener analyzer skill for DSL-based stock screening.

### `skills/performance_analyzer/skill.yml`

Performance analysis tools using run_tool.sh wrapper.

## Data Flow

```
User Input
    ↓
Hermes Agent (natural language understanding)
    ↓
Skill System (route to appropriate action)
    ↓
cresus-mcp CLI (execute command)
    ↓
REST API (http://192.168.0.130:6501/api/v1)
    ↓
Response → Hermes → User
```

## API Features

Portfolio responses include:
- **Company Names** - Now included in position data (enriched at source)
- **Structured Data** - JSON responses for reliable parsing
- **Real-time Prices** - Current market prices via Fundamental data
- **Performance Metrics** - Sharpe ratio, max drawdown, win rate, etc.

## Usage Examples

```bash
# List portfolios
hermes -q "list my portfolios"

# Portfolio positions with company names
hermes -q "show PEA positions"
# Returns: [{"ticker": "MC.PA", "company_name": "LVMH...", "quantity": 2, ...}]

# Performance comparison
hermes -q "compare PEA and BNP performance"

# Screener operations
hermes -q "create momentum screener with sha_14_green and rsi_14 > 50"

# Validation
hermes -q "validate formula: ema_20 > ema_50 and adx_14 > 25"
```

## Environment Setup

Key environment variables in `~/.hermes/.env`:

```bash
# Model
OLLAMA_BASE_URL=http://192.168.0.160:11434/v1
OLLAMA_NUM_CTX=32768

# API
CRESUS_API_URL=http://192.168.0.130:6501/api/v1

# Settings
HERMES_MAX_TOKENS=16384
HERMES_TEMPERATURE=0.2
```

## Troubleshooting

### "No tool calls executed"
- Verify Ollama is running: `curl http://192.168.0.160:11434/api/tags`
- Check context window: `sudo systemctl show ollama | grep OLLAMA_NUM_CTX`
- Should be 32768 or higher

### "Command not found: cresus-mcp"
- Ensure cresus is installed: `pip install -e .`
- Verify bin/cresus-mcp exists and is executable
- Check PATH: `which cresus-mcp`

### "Portfolio not found"
- List available: `cresus-mcp portfolio list`
- Ensure portfolio exists in ~/.cresus/db/portfolios/

### "API connection failed"
- Check API is running: `curl http://192.168.0.130:6501/api/v1/health`
- Verify IP and port in config.yaml
- Check network connectivity: `ping 192.168.0.130`

## Performance Tips

1. **Context Window** - Larger context (32K+) allows more comprehensive analysis
2. **Skill Caching** - Skills cache results automatically
3. **Batch Queries** - Combine multiple requests when possible
4. **Temperature** - Keep at 0.2 for accurate data retrieval

## Advanced Configuration

### Custom System Prompt

Edit `~/.hermes/config/system_prompt.md` to customize agent behavior and instructions.

### Modify Skill Triggers

Update trigger patterns in skill YAML files:
```yaml
triggers:
  - "portfolio"
  - "positions"
  - ".*portfolio.*"  # Regex patterns supported
```

## Logs

- Hermes logs: `~/.hermes/logs/`
- Cresus logs: `~/.cresus/logs/`
- Check for errors: `tail -f ~/.hermes/logs/*.log`

## Support

For issues:
1. Check logs in `~/.hermes/logs/` and `~/.cresus/logs/`
2. Test CLI directly: `cresus portfolio list`
3. Verify API: `curl http://192.168.0.130:6501/api/v1/health`
4. Review skill configs in `~/.hermes/skills/cresus/`

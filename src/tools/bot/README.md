# Bot Management System

The bot management system provides a complete framework for creating, managing, and controlling automated trading bots with isolated environments and persistent state.

## Overview

Each bot is a self-contained trading application with:
- **Strategy Configuration** - Copied from existing strategy files
- **Portfolio Management** - Isolated portfolio with positions and cash
- **Trade Journal** - CSV log of all trades
- **Watchlist** - List of tickers to monitor
- **State Management** - Active or inactive status
- **Configuration** - YAML-based settings and parameters

## Architecture

```
~/.cresus/db/bots/
├── momentum_cac40/
│   ├── config.yml              # Bot configuration (from template)
│   ├── strategy.yml            # Strategy (copied from source)
│   ├── portfolio.json          # Portfolio state
│   ├── journal.csv             # Trade journal
│   └── watchlist.txt           # Watchlist
├── mean_reversion_nasdaq/
│   ├── config.yml
│   ├── strategy.yml
│   ├── portfolio.json
│   ├── journal.csv
│   └── watchlist.txt
└── ...
```

## Quick Start

### Creating a Bot

```python
from tools.bot import BotManager

manager = BotManager()

# Create a bot with a strategy
config = manager.create_bot(
    name="momentum_cac40",
    strategy_path="config/strategies/momentum.yml"
)

print(f"Bot created: {config['name']}")
print(f"State: {config['state']}")  # "inactive"
```

### Listing Bots

```python
from tools.bot import BotManager

manager = BotManager()

# List all bots
all_bots = manager.list_bots()

# List only active bots
active_bots = manager.list_bots(state_filter="active")

# Get summary
summary = manager.get_bots_summary()
print(f"Active: {summary['active']}, Inactive: {summary['inactive']}")
```

### Managing Bot State

```python
# Activate a bot
manager.activate_bot("momentum_cac40")

# Deactivate a bot
manager.deactivate_bot("momentum_cac40")

# Check bot info
bot_config = manager.get_bot("momentum_cac40")
print(f"State: {bot_config['state']}")
```

### Managing Watchlist

```python
# Load watchlist
tickers = manager.load_watchlist("momentum_cac40")

# Add ticker
manager.add_to_watchlist("momentum_cac40", "AC.PA")

# Remove ticker
manager.remove_from_watchlist("momentum_cac40", "AC.PA")

# Save entire watchlist
manager.save_watchlist("momentum_cac40", ["AC.PA", "OR.PA", "CS.PA"])
```

### Managing Portfolio

```python
# Load portfolio
portfolio = manager.load_portfolio("momentum_cac40")

print(f"Cash: ${portfolio['cash']:,.2f}")
print(f"Total Value: ${portfolio['total_value']:,.2f}")
print(f"Positions: {len(portfolio['positions'])}")

# Update portfolio
portfolio['cash'] = 95000
portfolio['total_value'] = 105000
portfolio['pnl'] = 5000
portfolio['pnl_pct'] = 0.05

manager.save_portfolio("momentum_cac40", portfolio)
```

### Managing Configuration

```python
# Load configuration
config = manager.load_config("momentum_cac40")

# Modify configuration
config['description'] = "Updated description"
config['state'] = "active"

# Save configuration
manager.save_config("momentum_cac40", config)
```

### Getting Comprehensive Bot Info

```python
# Get all bot information
info = manager.get_bot_info("momentum_cac40")

config = info['config']
portfolio = info['portfolio']
watchlist = info['watchlist']
strategy_file = info['strategy_file']
bot_dir = info['bot_dir']

print(f"Config: {config}")
print(f"Portfolio Value: ${portfolio['total_value']:,.2f}")
print(f"Watchlist: {', '.join(watchlist)}")
print(f"Strategy File: {strategy_file}")
print(f"Bot Directory: {bot_dir}")
```

## Bot Configuration (config.yml)

Each bot has a configuration file created from `init/templates/bots.yml`:

```yaml
# Bot metadata
name: "momentum_cac40"
description: "Momentum strategy on CAC40"
created_at: "2026-06-18T10:30:00"
state: "inactive"

# Strategy reference
strategy: "momentum.yml"

# Portfolio configuration
portfolio:
  initial_capital: 100000
  risk_per_trade: 0.02
  max_drawdown: 0.20
  position_sizing: "fixed"
  fixed_position_size: 5000

# Trading parameters
trading:
  market_open: "09:00"
  market_close: "17:30"
  entry:
    signal_strength_min: 0.7
    max_positions: 10
  exit:
    stop_loss: 0.05
    take_profit: 0.10

# Risk management
risk_management:
  max_daily_loss: 0.05
  max_correlation: 0.7
  sector_limit: 0.30
  single_stock_limit: 0.10
```

## Portfolio File (portfolio.json)

Each bot maintains a portfolio file tracking positions and cash:

```json
{
  "bot_name": "momentum_cac40",
  "initial_capital": 100000,
  "cash": 95000,
  "total_value": 105000,
  "pnl": 5000,
  "pnl_pct": 0.05,
  "positions": [
    {
      "ticker": "AC.PA",
      "quantity": 100,
      "entry_price": 50.0,
      "current_price": 52.5,
      "pnl": 250,
      "pnl_pct": 0.05
    }
  ],
  "created_at": "2026-06-18T10:30:00"
}
```

## Trade Journal (journal.csv)

CSV file tracking all trades executed by the bot:

```csv
date,ticker,type,quantity,price,pnl,pnl_pct,notes
2026-06-18,AC.PA,buy,100,50.0,0,0.0,Momentum signal
2026-06-19,OR.PA,buy,50,30.0,0,0.0,RSI oversold
2026-06-20,AC.PA,sell,100,52.5,250,0.05,Take profit
```

## Watchlist (watchlist.txt)

Simple text file with one ticker per line:

```
# Watchlist for bot: momentum_cac40
# Add tickers one per line
AC.PA
OR.PA
CS.PA
GLE.PA
```

## BotManager API

### Methods

#### Create and Delete

```python
# Create a new bot
config = manager.create_bot(name, strategy_path, config=None)

# Delete a bot
deleted = manager.delete_bot(name)
```

#### List and Query

```python
# List all bots (optionally filtered by state)
bots = manager.list_bots(state_filter="active")

# Get single bot config
bot = manager.get_bot(name)

# Get comprehensive bot info
info = manager.get_bot_info(name)

# Get summary
summary = manager.get_bots_summary()  # {"active": 2, "inactive": 3, "total": 5}
```

#### State Management

```python
# Activate a bot
activated = manager.activate_bot(name)

# Deactivate a bot
deactivated = manager.deactivate_bot(name)
```

#### Configuration

```python
# Load configuration
config = manager.load_config(name)

# Save configuration
manager.save_config(name, config)
```

#### Portfolio

```python
# Load portfolio
portfolio = manager.load_portfolio(name)

# Save portfolio
manager.save_portfolio(name, portfolio)
```

#### Watchlist

```python
# Load watchlist
tickers = manager.load_watchlist(name)

# Save watchlist
manager.save_watchlist(name, tickers)

# Add to watchlist
added = manager.add_to_watchlist(name, ticker)

# Remove from watchlist
removed = manager.remove_from_watchlist(name, ticker)
```

#### File Paths

```python
# Get bot directory
bot_dir = manager.get_bot_dir(name)

# Get file paths
strategy_path = manager.get_strategy_path(name)
portfolio_path = manager.get_portfolio_path(name)
journal_path = manager.get_journal_path(name)
watchlist_path = manager.get_watchlist_path(name)
```

#### Cleanup

```python
# Delete old bots, keeping most recent
deleted_count = manager.cleanup_old_bots(keep_count=10, state_filter="inactive")
```

## CLI Commands

Use the `bot` command in the CLI:

```bash
# List all bots
cresus> bot list

# List only active bots
cresus> bot list active

# Create a bot
cresus> bot create momentum_cac40 config/strategies/momentum.yml

# Show bot info
cresus> bot info momentum_cac40

# Activate bot
cresus> bot activate momentum_cac40

# Deactivate bot
cresus> bot deactivate momentum_cac40

# Show bot portfolio
cresus> bot portfolio momentum_cac40

# Manage watchlist
cresus> bot watchlist momentum_cac40 show
cresus> bot watchlist momentum_cac40 add AC.PA
cresus> bot watchlist momentum_cac40 remove OR.PA

# Manage configuration
cresus> bot config momentum_cac40 show
cresus> bot config momentum_cac40 load new_config.yml
cresus> bot config momentum_cac40 save exported_config.yml

# Show summary
cresus> bot summary

# Delete bot
cresus> bot delete momentum_cac40
```

## Use Cases

### 1. Strategy Testing Pipeline

```python
from tools.bot import BotManager

manager = BotManager()

# Create multiple bots for different strategies
strategies = [
    ("momentum_cac40", "config/strategies/momentum.yml"),
    ("mean_reversion_cac", "config/strategies/mean_reversion.yml"),
    ("pairs_trade_tech", "config/strategies/pairs_trading.yml")
]

for bot_name, strategy_path in strategies:
    config = manager.create_bot(bot_name, strategy_path)
    print(f"Created {bot_name}")

# Activate top performers
top_bots = ["momentum_cac40", "pairs_trade_tech"]
for bot_name in top_bots:
    manager.activate_bot(bot_name)
    print(f"Activated {bot_name}")
```

### 2. Bot Monitoring

```python
# Get summary
summary = manager.get_bots_summary()

print(f"Trading Bots: {summary['total']}")
print(f"  Active: {summary['active']}")
print(f"  Inactive: {summary['inactive']}")

# Check active bots
active_bots = manager.list_bots(state_filter="active")

for bot in active_bots:
    portfolio = manager.load_portfolio(bot['name'])
    pnl_pct = portfolio.get('pnl_pct', 0)
    print(f"{bot['name']}: {pnl_pct:.2%} P&L")
```

### 3. Watchlist Management

```python
# Sync watchlist across bots
master_watchlist = ["AC.PA", "OR.PA", "CS.PA", "GLE.PA", "SAF.PA"]

bots = manager.list_bots(state_filter="active")

for bot in bots:
    manager.save_watchlist(bot['name'], master_watchlist)
    print(f"Updated watchlist for {bot['name']}")
```

### 4. Portfolio Consolidation

```python
# Consolidate portfolio data from all bots
all_portfolios = {}

bots = manager.list_bots()

for bot in bots:
    portfolio = manager.load_portfolio(bot['name'])
    all_portfolios[bot['name']] = portfolio

# Calculate total
total_value = sum(p.get('total_value', 0) for p in all_portfolios.values())
total_pnl = sum(p.get('pnl', 0) for p in all_portfolios.values())

print(f"Total Portfolio Value: ${total_value:,.2f}")
print(f"Total P&L: ${total_pnl:,.2f}")
```

## File Structure

```
~/.cresus/db/bots/
├── momentum_cac40/
│   ├── config.yml
│   ├── strategy.yml
│   ├── portfolio.json
│   ├── journal.csv
│   └── watchlist.txt
└── ...
```

## Template Configuration

The default bot template is stored at `init/templates/bots.yml` and automatically copied to each bot's `config.yml` on creation.

## Integration

### With Jobs System

Use bots with the jobs system to automate trading:

```python
from jobs import BotBacktest
from tools.bot import BotManager

bot_manager = BotManager()
bot = bot_manager.get_bot("momentum_cac40")

# Load bot strategy for backtesting
strategy = bot.get('strategy')
```

### With Portfolio System

Bots maintain their own portfolios separate from main portfolios:

```python
# Bot portfolio
bot_portfolio = bot_manager.load_portfolio("momentum_cac40")

# Update based on trading
bot_portfolio['cash'] -= 5000
bot_portfolio['total_value'] -= 5000
bot_manager.save_portfolio("momentum_cac40", bot_portfolio)
```

## Best Practices

1. **Naming Convention**: Use descriptive names: `{strategy}_{market}_{version}`
   - `momentum_cac40_v1`
   - `mean_reversion_nasdaq_v2`
   - `pairs_trading_tech_v1`

2. **Configuration**: Use the template `init/templates/bots.yml` for consistency

3. **Isolation**: Each bot operates independently with its own portfolio and journal

4. **Activation**: Only activate bots that have been thoroughly backtested

5. **Monitoring**: Regularly check portfolio performance and P&L

6. **Cleanup**: Use `cleanup_old_bots()` to remove old bots periodically

## See Also

- `init/templates/bots.yml` - Default bot template
- `src/cli/commands/bots.py` - CLI command implementation
- `src/tools/jobs/` - Job management system for automation

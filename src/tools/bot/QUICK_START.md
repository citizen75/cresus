# Bot Management Quick Start

## Overview

The bot management system provides complete lifecycle management for automated trading bots:

- **Isolated Environments** - Each bot has its own configuration, portfolio, and journal
- **Strategy Integration** - Bots use existing strategy files from your config
- **Portfolio Management** - Track positions, cash, and P&L independently
- **State Management** - Activate/deactivate bots for live trading
- **Watchlist** - Monitor specific tickers per bot

## Installation

Bots are part of the Cresus package. Import and use:

```python
from tools.bot import BotManager

manager = BotManager()
```

## Quick Examples

### Create a Bot

```python
from tools.bot import BotManager

manager = BotManager()

# Create bot with a strategy
config = manager.create_bot(
    name="momentum_cac40",
    strategy_path="config/strategies/momentum.yml"
)

print(f"Bot created: {config['name']}")
print(f"State: {config['state']}")  # "inactive"
```

### List Bots

```python
# List all bots
all_bots = manager.list_bots()

# List only active bots
active_bots = manager.list_bots(state_filter="active")

# Get summary
summary = manager.get_bots_summary()
# {"active": 2, "inactive": 3, "total": 5}
```

### Activate/Deactivate Bot

```python
# Activate for live trading
manager.activate_bot("momentum_cac40")

# Deactivate when done
manager.deactivate_bot("momentum_cac40")

# Check status
bot = manager.get_bot("momentum_cac40")
print(f"State: {bot['state']}")  # "active" or "inactive"
```

### Manage Watchlist

```python
# Add tickers
manager.add_to_watchlist("momentum_cac40", "AC.PA")
manager.add_to_watchlist("momentum_cac40", "OR.PA")

# View watchlist
tickers = manager.load_watchlist("momentum_cac40")
# ["AC.PA", "OR.PA"]

# Remove ticker
manager.remove_from_watchlist("momentum_cac40", "AC.PA")

# Set entire watchlist
manager.save_watchlist("momentum_cac40", ["AC.PA", "OR.PA", "CS.PA"])
```

### View Portfolio

```python
# Load portfolio
portfolio = manager.load_portfolio("momentum_cac40")

print(f"Capital: ${portfolio['initial_capital']:,.2f}")
print(f"Cash: ${portfolio['cash']:,.2f}")
print(f"Total Value: ${portfolio['total_value']:,.2f}")
print(f"P&L: ${portfolio['pnl']:,.2f} ({portfolio['pnl_pct']:.2%})")
print(f"Positions: {len(portfolio['positions'])}")

# Update portfolio
portfolio['cash'] = 95000
portfolio['total_value'] = 105000
portfolio['pnl'] = 5000
portfolio['pnl_pct'] = 0.05
manager.save_portfolio("momentum_cac40", portfolio)
```

### Get Full Bot Info

```python
# Get everything about a bot
info = manager.get_bot_info("momentum_cac40")

config = info['config']
portfolio = info['portfolio']
watchlist = info['watchlist']
bot_dir = info['bot_dir']

print(f"Name: {config['name']}")
print(f"State: {config['state']}")
print(f"Portfolio Value: ${portfolio['total_value']:,.2f}")
print(f"Watchlist: {', '.join(watchlist)}")
```

## CLI Usage

```bash
# List all bots
cresus> bot list

# List active bots
cresus> bot list active

# Create bot
cresus> bot create momentum_cac40 config/strategies/momentum.yml

# Show bot details
cresus> bot info momentum_cac40

# Activate bot
cresus> bot activate momentum_cac40

# Deactivate bot
cresus> bot deactivate momentum_cac40

# Show portfolio
cresus> bot portfolio momentum_cac40

# Manage watchlist
cresus> bot watchlist momentum_cac40 show
cresus> bot watchlist momentum_cac40 add AC.PA
cresus> bot watchlist momentum_cac40 remove OR.PA

# Manage configuration
cresus> bot config momentum_cac40 show
cresus> bot config momentum_cac40 load new_config.yml

# Show summary
cresus> bot summary

# Delete bot
cresus> bot delete momentum_cac40
```

## Bot File Structure

```
~/.cresus/db/bots/momentum_cac40/
├── config.yml          # Bot configuration (from template)
├── strategy.yml        # Strategy (copied from source)
├── portfolio.json      # Portfolio state
├── journal.csv         # Trade journal
└── watchlist.txt       # Watchlist of tickers
```

## Bot Configuration (config.yml)

Bots use a template-based configuration from `init/templates/bots.yml`:

```yaml
name: "momentum_cac40"
state: "inactive"
strategy: "momentum"

portfolio:
  initial_capital: 100000
  risk_per_trade: 0.02
  max_drawdown: 0.20

trading:
  market_open: "09:00"
  market_close: "17:30"
  entry:
    signal_strength_min: 0.7
    max_positions: 10
  exit:
    stop_loss: 0.05
    take_profit: 0.10
```

## Portfolio File (portfolio.json)

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
  ]
}
```

## Common Patterns

### Create Multiple Bots

```python
strategies = [
    "momentum.yml",
    "mean_reversion.yml",
    "pairs_trading.yml"
]

for strategy in strategies:
    bot_name = Path(strategy).stem
    manager.create_bot(bot_name, f"config/strategies/{strategy}")
```

### Activate Top Performers

```python
# Get all bots sorted by P&L
all_bots = manager.list_bots()
sorted_bots = sorted(
    all_bots,
    key=lambda b: manager.load_portfolio(b['name']).get('pnl_pct', 0),
    reverse=True
)

# Activate top 3
for bot in sorted_bots[:3]:
    manager.activate_bot(bot['name'])
    print(f"Activated {bot['name']}")
```

### Monitor Active Bots

```python
active = manager.list_bots(state_filter="active")

for bot in active:
    portfolio = manager.load_portfolio(bot['name'])
    pnl = portfolio.get('pnl', 0)
    pnl_pct = portfolio.get('pnl_pct', 0)
    print(f"{bot['name']}: ${pnl:,.2f} ({pnl_pct:.2%})")
```

### Sync Watchlists

```python
# Master watchlist
master = ["AC.PA", "OR.PA", "CS.PA"]

# Apply to all bots
active_bots = manager.list_bots(state_filter="active")
for bot in active_bots:
    manager.save_watchlist(bot['name'], master)
```

### Consolidate Portfolio Data

```python
total_value = 0
total_pnl = 0

for bot in manager.list_bots():
    portfolio = manager.load_portfolio(bot['name'])
    total_value += portfolio.get('total_value', 0)
    total_pnl += portfolio.get('pnl', 0)

print(f"Total: ${total_value:,.2f}")
print(f"Total P&L: ${total_pnl:,.2f}")
```

## Best Practices

1. **Naming**: Use descriptive names
   - `momentum_cac40_v1`
   - `mean_reversion_nasdaq_v2`
   - `pairs_trading_tech_v1`

2. **Configuration**: Always use template for consistency

3. **Isolation**: Each bot operates independently

4. **Activation**: Only activate after backtesting

5. **Monitoring**: Regularly check portfolio performance

6. **Cleanup**: Remove old/poor performing bots

## File Locations

- **Configuration**: `init/templates/bots.yml`
- **Bots Directory**: `~/.cresus/db/bots/`
- **Individual Bot**: `~/.cresus/db/bots/<bot_name>/`

## Troubleshooting

**Bot already exists error:**
```python
# Delete old bot first
manager.delete_bot("bot_name")
# Then create new one
manager.create_bot("bot_name", strategy_path)
```

**Strategy file not found:**
```python
# Make sure strategy file exists
from pathlib import Path
strategy = Path("config/strategies/momentum.yml")
assert strategy.exists(), f"Strategy not found: {strategy}"

manager.create_bot("my_bot", str(strategy))
```

**Portfolio not updating:**
```python
# Don't forget to save!
portfolio = manager.load_portfolio("bot_name")
portfolio['cash'] = 95000
manager.save_portfolio("bot_name", portfolio)  # Must save!
```

## Examples

See `src/tools/bot/examples.py` for complete working examples:

```bash
python src/tools/bot/examples.py
```

## Documentation

- **Full API**: See `README.md`
- **Examples**: See `examples.py`
- **Tests**: See `tests/tools/test_bot_manager.py`

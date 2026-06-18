# Bot CLI Commands Reference

Comprehensive guide to managing trading bots via the Cresus CLI.

## Overview

The `bot` command provides full control over trading bot lifecycle:
- Create bots from existing strategies
- Activate/deactivate for trading
- Manage portfolio, watchlist, and configuration
- Monitor bot performance
- List and filter bots by state

## Quick Start

```bash
# List all bots
cresus> bot list

# Create a bot with a strategy
cresus> bot create cac_bot cac_top_5

# Activate for trading
cresus> bot activate cac_bot

# Show bot details
cresus> bot info cac_bot

# Stop trading
cresus> bot deactivate cac_bot
```

## Commands Reference

### List Bots

**List all bots:**
```bash
cresus> bot list
```

**List bots by state:**
```bash
cresus> bot list active      # Active bots only
cresus> bot list inactive    # Inactive bots only
```

**Output:**
```
                                              Bots (active)
╭──────────────────┬─────────┬────────────┬──────────────────╮
│ Name             │ State   │ Strategy   │ Created          │
├──────────────────┼─────────┼────────────┼──────────────────┤
│ momentum_cac40   │ active  │ momentum   │ 2026-06-18       │
│ mean_reversion   │ active  │ reversal   │ 2026-06-17       │
╰──────────────────┴─────────┴────────────┴──────────────────╯
```

---

### Create Bot

**Create a bot with strategy name:**
```bash
cresus> bot create cac_bot cac_top_5
cresus> bot create momentum_bot cac_momentum
```

**Create a bot with strategy path:**
```bash
cresus> bot create my_bot config/strategies/momentum.yml
cresus> bot create test_bot ./strategies/custom.yml
```

**Output:**
```
✓ Bot created: cac_bot
  Directory: ~/.cresus/db/bots/cac_bot
  Strategy: cac_top_5
  State: inactive
```

**Strategy Resolution:**
When you provide a strategy name, Cresus searches in order:
1. `config/strategies/<name>.yml`
2. `config/<name>.yml`
3. `strategies/<name>.yml`
4. `<name>.yml`
5. Full path if provided

---

### Show Bot Information

**Display all bot details:**
```bash
cresus> bot info cac_bot
```

**Output:**
```
╭─────────────────────────────────────────────╮
│ Bot: cac_bot                                │
├─────────────────────────────────────────────┤
│ State: active                               │
│ Created: 2026-06-18T10:30:00                │
│ Strategy: cac_top_5                         │
│ Description: Top 5 CAC40 stocks by momentum │
│                                             │
│ Portfolio:                                  │
│   Capital: $100,000.00                      │
│   Cash: $95,000.00                          │
│   Total Value: $105,000.00                  │
│   P&L: $5,000.00 (5.00%)                    │
│   Positions: 1                              │
│                                             │
│ Watchlist:                                  │
│   AC.PA, OR.PA, CS.PA, GLE.PA, SAF.PA       │
╰─────────────────────────────────────────────╯
```

---

### Run Bot

**Execute bot trading cycle:**
```bash
cresus> bot run cac_bot
```

**Run with custom parameters:**
```bash
cresus> bot run cac_bot '{"market":"cac40","capital":100000,"signal_strength":0.7}'
```

**Requirements:**
- Bot must be ACTIVE (activate first: `bot activate <name>`)
- Parameters are optional (default empty dict)

**Output:**
```
Running bot: cac_bot
Params: {"market": "cac40", "capital": 100000}

                                    Bot Execution Results: cac_bot
╭─────────────────────────┬──────────────────╮
│ Metric                  │ Value            │
├─────────────────────────┼──────────────────┤
│ Status                  │ ✓ Success        │
│ Execution Time          │ 123.45ms         │
│ Trades Executed         │ 2                │
│ P&L                     │ $1,500.00        │
│ Positions               │ 1                │
╰─────────────────────────┴──────────────────╯
```

**Error if bot not active:**
```
Bot is not active: cac_bot
Activate with: bot activate cac_bot
```

---

### Activate Bot

**Activate a bot for live trading:**
```bash
cresus> bot activate cac_bot
```

**Output:**
```
✓ Bot activated: cac_bot
```

---

### Deactivate Bot

**Stop trading with a bot:**
```bash
cresus> bot deactivate cac_bot
```

**Output:**
```
✓ Bot deactivated: cac_bot
```

---

### Delete Bot

**Remove a bot and all its data:**
```bash
cresus> bot delete cac_bot
```

**Output:**
```
✓ Bot deleted: cac_bot
```

⚠️ **Warning**: This removes all bot data including portfolio, journal, and configuration.

---

### Manage Configuration

**Show bot configuration:**
```bash
cresus> bot config cac_bot show
```

**Output:**
```
name: cac_bot
state: active
description: Top 5 CAC40 stocks
strategy: cac_top_5
created_at: '2026-06-18T10:30:00'
activated_at: '2026-06-18T10:31:00'

portfolio:
  initial_capital: 100000
  risk_per_trade: 0.02
  max_drawdown: 0.20
  position_sizing: fixed
  fixed_position_size: 5000

trading:
  market_open: '09:00'
  market_close: '17:30'
  entry:
    signal_strength_min: 0.7
    max_positions: 10
  exit:
    stop_loss: 0.05
    take_profit: 0.10
```

**Load configuration from file:**
```bash
cresus> bot config cac_bot load my_config.yml
```

**Output:**
```
✓ Configuration loaded from: my_config.yml
```

**Save configuration to file:**
```bash
cresus> bot config cac_bot save exported_config.yml
```

**Output:**
```
✓ Configuration saved to: exported_config.yml
```

---

### Manage Watchlist

**Show bot watchlist:**
```bash
cresus> bot watchlist cac_bot show
```

**Output:**
```
                                        Watchlist: cac_bot
╭──────────╮
│ Ticker   │
├──────────┤
│ AC.PA    │
│ OR.PA    │
│ CS.PA    │
│ GLE.PA   │
│ SAF.PA   │
╰──────────╯
```

**Add ticker to watchlist:**
```bash
cresus> bot watchlist cac_bot add BNP.PA
```

**Output:**
```
✓ Added to watchlist: BNP.PA
```

**Remove ticker from watchlist:**
```bash
cresus> bot watchlist cac_bot remove BNP.PA
```

**Output:**
```
✓ Removed from watchlist: BNP.PA
```

---

### Show Portfolio

**Display bot portfolio:**
```bash
cresus> bot portfolio cac_bot
```

**Output:**
```
╭─────────────────────────────────────────────╮
│ Portfolio: cac_bot                          │
├─────────────────────────────────────────────┤
│ Capital: $100,000.00                        │
│ Cash: $95,000.00                            │
│ Total Value: $105,000.00                    │
│ P&L: $5,000.00 (5.00%)                      │
│ Positions: 1                                │
╰─────────────────────────────────────────────╯

                                           Positions
╭──────────┬──────────┬────────────┬──────────────┬────────────╮
│ Ticker   │ Quantity │ Entry Price│ Current Price│ P&L        │
├──────────┼──────────┼────────────┼──────────────┼────────────┤
│ AC.PA    │ 100      │ $50.00     │ $52.50       │ $250.00    │
╰──────────┴──────────┴────────────┴──────────────┴────────────╯
```

---

### Show Summary

**Get count of bots by state:**
```bash
cresus> bot summary
```

**Output:**
```
                                           Bot Summary
╭───────────┬───────╮
│ State     │ Count │
├───────────┼───────┤
│ active    │ 2     │
│ inactive  │ 3     │
│ Total     │ 5     │
╰───────────┴───────╯
```

---

## Common Workflows

### Deploy a New Strategy

```bash
# Step 1: Create bot from strategy
cresus> bot create momentum_v1 cac_momentum

# Step 2: Verify configuration
cresus> bot info momentum_v1

# Step 3: Set watchlist
cresus> bot watchlist momentum_v1 add AC.PA
cresus> bot watchlist momentum_v1 add OR.PA

# Step 4: Activate for trading
cresus> bot activate momentum_v1

# Step 5: Run execution cycle
cresus> bot run momentum_v1

# Step 6: Monitor portfolio
cresus> bot portfolio momentum_v1
```

### Running Bot with Custom Parameters

```bash
# Activate bot
cresus> bot activate momentum_v1

# Run with market parameter
cresus> bot run momentum_v1 '{"market":"cac40"}'

# Run with multiple parameters
cresus> bot run momentum_v1 '{"market":"cac40","capital":100000,"signal_strength":0.7}'

# Check results
cresus> bot portfolio momentum_v1
```

### Monitor Active Bots

```bash
# List active bots
cresus> bot list active

# Check each bot's performance
cresus> bot portfolio momentum_v1
cresus> bot portfolio mean_reversion_v1
```

### Pause and Resume Trading

```bash
# Pause all trading (deactivate bots)
cresus> bot deactivate momentum_v1
cresus> bot deactivate mean_reversion_v1

# Resume trading
cresus> bot activate momentum_v1
```

### Manage Watchlists Across Bots

```bash
# Add same ticker to multiple bots
cresus> bot watchlist momentum_v1 add AC.PA
cresus> bot watchlist mean_reversion_v1 add AC.PA
cresus> bot watchlist pairs_trading_v1 add AC.PA
```

### Archive Old Bot

```bash
# View old bot
cresus> bot info old_strategy

# Get results (export config/portfolio before deleting)
cresus> bot config old_strategy save old_strategy_config.yml

# Delete
cresus> bot delete old_strategy
```

---

## Bot File Structure

Each bot creates files at `~/.cresus/db/bots/<bot_name>/`:

```
~/.cresus/db/bots/momentum_v1/
├── config.yml              # Bot configuration
├── strategy.yml            # Strategy definition
├── portfolio.json          # Portfolio state
├── journal.csv             # Trade journal
└── watchlist.txt           # Watchlist of tickers
```

**Access bot files:**
```bash
# View raw config
cat ~/.cresus/db/bots/momentum_v1/config.yml

# View portfolio
cat ~/.cresus/db/bots/momentum_v1/portfolio.json

# View trades
cat ~/.cresus/db/bots/momentum_v1/journal.csv
```

---

## Bot States

| State | Description | Can Trade |
|-------|---|---|
| `active` | Bot is enabled for trading | Yes |
| `inactive` | Bot is paused | No |

**State Transitions:**
```
inactive → (activate) → active
active → (deactivate) → inactive
```

---

## Configuration

Each bot uses a configuration copied from `init/templates/bots.yml`.

**Key sections:**
- `portfolio` - Capital, risk, position sizing
- `trading` - Market hours, entry/exit rules
- `risk_management` - Max drawdown, correlations, limits
- `watchlist` - Tickers to monitor
- `notifications` - Alert channels

**Example config:**
```yaml
name: momentum_v1
state: inactive
strategy: cac_momentum

portfolio:
  initial_capital: 100000
  risk_per_trade: 0.02
  max_drawdown: 0.20

trading:
  market_open: "09:00"
  market_close: "17:30"
  exit:
    stop_loss: 0.05
    take_profit: 0.10
```

---

## Tips & Tricks

### Find Strategy Names
```bash
# List available strategies
cresus> strategy list

# Use any strategy name in bot create command
cresus> bot create my_bot cac_top_5
```

### Batch Operations
```bash
# Create multiple bots
cresus> bot create momentum_cac cac_momentum
cresus> bot create momentum_nasdaq nasdaq_momentum
cresus> bot create pairs_tech pairs_trading

# Activate all
cresus> bot activate momentum_cac
cresus> bot activate momentum_nasdaq
cresus> bot activate pairs_tech

# Check all
cresus> bot list active
```

### Export Before Deleting
```bash
# Always save config and results first
cresus> bot config old_bot save old_bot_backup.yml

# Then delete
cresus> bot delete old_bot
```

### Monitor Performance
```bash
# Check active bots
cresus> bot list active

# Show summary
cresus> bot summary

# Get portfolio for top performer
cresus> bot portfolio momentum_v1
```

---

## Troubleshooting

**Bot creation fails with "Strategy file not found":**
```bash
# Make sure strategy exists
cresus> strategy list

# Check if name matches
cresus> bot create my_bot cac_top_5  # Use exact strategy name
```

**Bot not appearing in list:**
```bash
# Check inactive bots
cresus> bot list inactive

# Get bot info directly
cresus> bot info bot_name
```

**Portfolio not updating:**
```bash
# Portfolio is stored in bot directory
ls ~/.cresus/db/bots/bot_name/

# View current portfolio
cresus> bot portfolio bot_name
```

---

## See Also

- **Bot API**: `src/tools/bot/README.md` - Python API reference
- **Bot Manager**: `src/tools/bot/__init__.py` - Implementation
- **Examples**: `src/tools/bot/examples.py` - Working code examples
- **Tests**: `tests/tools/test_bot_manager.py` - Test suite

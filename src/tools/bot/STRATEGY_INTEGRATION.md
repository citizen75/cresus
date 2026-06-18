# Bot and Strategy Integration

This document explains how bots integrate with the Cresus strategy system.

## Overview

Bots use strategies defined in your project's strategy system. When you create a bot with a strategy name, Cresus automatically:

1. Finds the strategy from the strategy system (via StrategyManager)
2. Extracts the strategy configuration
3. Copies it to the bot's isolated environment
4. Creates a bot with that strategy configuration

## Finding Available Strategies

### Via CLI

```bash
# List all available strategies
cresus> strategy list
```

Output shows all strategies with details:
```
                                            Strategies (40)
╭───────────────────────┬──────────────┬──────────────────────────────────────────────────────────────╮
│ Strategy              │ Universe     │ Description                                                  │
├───────────────────────┼──────────────┼──────────────────────────────────────────────────────────────┤
│ cac_momentum          │ cac40        │ Brief description of strategy objectives and logic           │
│ cac_strategy1         │ N/A          │                                                              │
│ cac_strategy2         │ N/A          │                                                              │
│ cac_top_5             │ cac40        │ Brief description of strategy objectives and logic           │
│ mean_reversion        │ nasdaq       │ ...                                                          │
...
```

### Via Python

```python
from tools.strategy import StrategyManager

manager = StrategyManager()
strategies = manager.list_strategies()

for strategy in strategies.get("strategies", []):
    print(f"Name: {strategy['name']}")
    print(f"Universe: {strategy.get('universe', 'N/A')}")
    print(f"Description: {strategy.get('description', '-')}")
    print()
```

## Creating a Bot from Strategy

### Method 1: Using Strategy Name

```bash
# Using strategy name from strategy system
cresus> bot create cac_bot cac_top_5
cresus> bot create momentum_bot cac_momentum
cresus> bot create nasdaq_bot nasdaq_strategy
```

Cresus automatically:
- Finds the strategy
- Extracts its configuration
- Creates the bot with that strategy

### Method 2: Using File Path

If you have a strategy saved as a YAML file:

```bash
# Using file path (backward compatible)
cresus> bot create my_bot config/strategies/momentum.yml
cresus> bot create test_bot ./my_strategy.yml
```

## Strategy Resolution

When you use a strategy name, Cresus searches in order:

1. Direct file path (if you provide full path)
2. `config/strategies/<name>.yml`
3. `config/<name>.yml`
4. `strategies/<name>.yml`
5. `<name>.yml`
6. StrategyManager system (strategies from YAML config)

## What Gets Copied

When a bot is created, here's what happens:

### Bot Directory Structure
```
~/.cresus/db/bots/my_bot/
├── config.yml          # Bot configuration (from template)
├── strategy.yml        # Strategy copy (from StrategyManager)
├── portfolio.json      # Initialized portfolio
├── journal.csv         # Empty trade journal
└── watchlist.txt       # Empty watchlist
```

### strategy.yml
Contains the strategy definition extracted from the strategy system:
- Indicators
- Buy/sell conditions
- Signal definitions
- Strategy parameters
- Etc.

## Using Bot Strategies

### View Strategy

```bash
# View bot's strategy configuration
cat ~/.cresus/db/bots/my_bot/strategy.yml
```

### Modify Strategy

```python
from tools.bot import BotManager
import yaml

manager = BotManager()

# Load bot's strategy
with open(manager.get_strategy_path("my_bot")) as f:
    strategy = yaml.safe_load(f)

# Modify strategy
strategy['signals'].append('new_signal')

# Update bot's strategy
bot_dir = manager.get_bot_dir("my_bot")
with open(bot_dir / "strategy.yml", "w") as f:
    yaml.dump(strategy, f)
```

## Example Workflows

### Deploy Strategy to Multiple Bots

```bash
# Create multiple bots from same strategy
cresus> bot create momentum_cac cac_momentum
cresus> bot create momentum_nasdaq nasdaq_momentum
cresus> bot create momentum_dow dow_momentum

# List all
cresus> bot list

# Check each
cresus> bot info momentum_cac
cresus> bot info momentum_nasdaq
cresus> bot info momentum_dow
```

### Test Strategy in Bot

```bash
# 1. Create bot
cresus> bot create test_bot experimental_strategy

# 2. Review strategy
cresus> bot config test_bot show

# 3. Set watchlist for testing
cresus> bot watchlist test_bot add AC.PA
cresus> bot watchlist test_bot add OR.PA

# 4. Activate for testing
cresus> bot activate test_bot

# 5. Monitor
cresus> bot portfolio test_bot

# 6. Review results
cresus> bot info test_bot
```

### Create Multiple Bots from All Available Strategies

```python
from tools.strategy import StrategyManager
from tools.bot import BotManager

strategy_manager = StrategyManager()
bot_manager = BotManager()

# Get all strategies
strategies = strategy_manager.list_strategies()

# Create bots
for strategy in strategies.get("strategies", []):
    strategy_name = strategy['name']
    bot_name = f"bot_{strategy_name}"

    try:
        config = bot_manager.create_bot(bot_name, strategy_name)
        print(f"✓ Created {bot_name} with strategy {strategy_name}")
    except ValueError as e:
        print(f"✗ Failed to create {bot_name}: {e}")
```

## Troubleshooting

### Strategy Not Found

**Error:**
```
✗ Error: Strategy file not found: cac_top_5
Available strategies: cac_momentum, cac_strategy1, cac_strategy2, ...
Use 'cresus strategy list' to see all strategies
```

**Solution:**
1. Check available strategies: `cresus strategy list`
2. Use correct strategy name
3. Verify strategy exists in your configuration

### Strategy File Corrupted

**Symptoms:**
- Bot creation fails
- Strategy won't load

**Solution:**
1. Verify strategy in system: `cresus strategy check <strategy_name>`
2. Fix strategy if needed: `cresus strategy fix <strategy_name>`
3. Create bot again

### Cannot Find Strategy File

**Error:**
```
Strategy file not found: cac_top_5
```

**Possible causes:**
1. Strategy name doesn't match exactly (case-sensitive)
2. Strategy file not in expected location
3. Strategy not registered in system

**Solution:**
```bash
# List strategies to see exact names
cresus strategy list

# Use exact name from list
cresus bot create my_bot exact_strategy_name
```

## Integration Points

### With StrategyManager

Bots use StrategyManager to:
- List available strategies
- Load strategy configurations
- Validate strategies
- Extract strategy definitions

### With Portfolio

Bot portfolios start fresh:
- Initial capital: from bot config
- Cash: equals initial capital
- Positions: empty
- P&L: 0

### With Watchlist

Each bot can have its own watchlist:
- Independent from strategy's watchlist
- Used to filter signals
- Can be modified per bot

## Best Practices

1. **Name Bots After Strategy + Market**: `momentum_cac40`, `mean_reversion_nasdaq`

2. **Verify Strategy Before Creating Bot**:
   ```bash
   cresus strategy check strategy_name
   cresus bot create my_bot strategy_name
   ```

3. **Use Consistent Configuration**: Bots use the template from `init/templates/bots.yml`

4. **Isolate Bot Environments**: Each bot's strategy is copied, not referenced

5. **Backup Strategies**: Save strategy before making bots
   ```bash
   cresus strategy export my_strategy > backup.yml
   ```

## Advanced Usage

### Copy Bot's Strategy to Create New Bot

```bash
# 1. Export bot's strategy
cp ~/.cresus/db/bots/bot1/strategy.yml /tmp/my_strategy.yml

# 2. Create new bot with that strategy
cresus bot create bot2 /tmp/my_strategy.yml
```

### Extract Strategy for Manual Use

```python
from tools.bot import BotManager
import yaml

manager = BotManager()

# Get bot's strategy
strategy_path = manager.get_strategy_path("my_bot")
with open(strategy_path) as f:
    strategy = yaml.safe_load(f)

# Use strategy elsewhere
print(strategy['buy_conditions'])
print(strategy['sell_conditions'])
```

### Migrate Strategy Between Projects

```bash
# Export from source bot
cp ~/.cresus/db/bots/source_bot/strategy.yml strategy_backup.yml

# Create bot in new project
cresus bot create migrated_bot strategy_backup.yml
```

## See Also

- **StrategyManager**: `src/tools/strategy/strategy.py`
- **Bot Manager**: `src/tools/bot/__init__.py`
- **CLI Commands**: `BOTS_CLI.md`
- **Strategy System**: See CLAUDE.md project documentation

# Strategy Template and Validation System

## Overview

A comprehensive system for ensuring all strategies follow a consistent format and are compliant with requirements.

## Components

### 1. Strategy Template
**Location:** `/init/templates/strategy.yml`

Defines the standard structure that all strategies must follow:
- Required top-level fields: `name`, `universe`, `description`, `engine`, `indicators`
- Required sections: `watchlist`, `signals`, `entry`, `exit`, `backtest`
- Required parameters in each section
- Default values and descriptions for all fields

### 2. StrategyManager Functions

Added to `src/tools/strategy/strategy.py`:

#### `check_strategy(strategy_name: str) -> Dict`
Validates a strategy against the template schema and returns:
- `valid`: boolean indicating compliance
- `issues`: list of missing fields or invalid configurations
- `issue_count`: number of issues found
- `required_fields`: list of missing required fields

Example:
```python
sm = StrategyManager()
result = sm.check_strategy('my_strategy')
if not result['valid']:
    print(f"Issues found: {result['issues']}")
```

#### `fix_strategy(strategy_name: str, dry_run: bool = False) -> Dict`
Automatically fixes strategy compliance by:
- Adding missing required fields with defaults from template
- Adding missing required sections
- Commenting out invalid/unknown keys with `_invalid_` prefix
- Returns list of changes made

Example:
```python
sm = StrategyManager()
result = sm.fix_strategy('my_strategy')  # Fixes and saves
print(f"Changes: {result['changes']}")
```

#### `_load_template() -> Dict`
Internal function that loads the template structure from `init/templates/strategy.yml`.

### 3. CLI Command Updates

Updated `src/cli/commands/strategy.py`:

#### `cresus strategy check <strategy_name>`
Check if a strategy is compliant with template:
```bash
cresus strategy check cac_momentum
```

Output shows:
- Compliance status (✓ valid or ✗ issues)
- List of issues found
- Suggestion to use `--fix` flag

#### `cresus strategy check <strategy_name> --fix`
Automatically fix non-compliant strategies:
```bash
cresus strategy check my_strategy --fix
```

Changes are:
- Saved to the strategy file
- Displayed in the console with ✓ checkmarks

#### `cresus strategy check --template`
Display the strategy template:
```bash
cresus strategy check --template
```

## Validation Rules

### Required Top-Level Fields
- `name`: Strategy identifier
- `universe`: Data source (cac40, nasdaq_100, etc.)
- `description`: Strategy description
- `engine`: Analysis engine (TaModel, LightGbmModel, etc.)
- `indicators`: List of technical indicators to use

### Required Sections
Each strategy must have these sections:
- `watchlist`: Ticker selection configuration
- `signals`: Signal generation configuration
- `entry`: Entry rule parameters
- `exit`: Exit rule parameters
- `backtest`: Backtesting configuration

### Required Parameters
**Entry Section:**
- `position_size`: Formula for position sizing

**Exit Section:**
- `stop_loss`: Formula for stop loss (required for risk management)
- `holding_period`: Maximum holding period in days

## Examples

### Check existing strategy
```bash
$ cresus strategy check cac_momentum
✓ Strategy is compliant with template
```

### Fix non-compliant strategy
```bash
$ cresus strategy check my_strategy --fix
✗ 3 issue(s) found:
  • Missing required field: engine
  • Missing section: backtest
  • Missing exit.parameters.stop_loss

✓ Strategy fixed
  • Added missing field: engine
  • Added missing section: backtest
  • Added exit.parameters.stop_loss
```

### Using StrategyManager programmatically
```python
from src.tools.strategy.strategy import StrategyManager

sm = StrategyManager()

# Check compliance
result = sm.check_strategy('my_strategy')
if result['valid']:
    print("Strategy is ready!")
else:
    # Fix it
    fix_result = sm.fix_strategy('my_strategy')
    print(f"Fixed {len(fix_result['changes'])} issues")
```

## Template Structure

The template covers:
- **Watchlist Configuration**: Ticker filtering criteria (trend, volatility, volume)
- **Signals**: Signal generation with weighted contributions
- **Entry Rules**: Entry filters, position sizing, timing
- **Exit Rules**: Stop loss, take profit, trailing stops, holding periods
- **Backtesting**: Initial capital and testing parameters

## Benefits

1. **Consistency**: All strategies follow the same structure
2. **Completeness**: Required fields are enforced
3. **Auto-fix**: Non-compliant strategies can be automatically corrected
4. **Clarity**: Template documents expected fields and their purpose
5. **Validation**: Easy to verify strategies before deployment

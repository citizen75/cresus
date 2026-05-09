# Indicators DSL Engine & Formula Syntax - Complete Guide

## Overview

The Indicators DSL Engine provides:

- **Indicator DSL**: Simple parameter syntax (e.g., `rsi_14`, `ema_20`, `bb_20_2`)
- **Formula DSL**: Simplified condition syntax for buy/sell rules and trend signals
- **Selective Calculation**: Only compute requested indicators
- **History Support**: Optional historical data to avoid redundant lookups
- **Strict Validation**: Clear error messages on invalid parameters
- **Type Organization**: Indicators grouped by category

## Indicators API

### Main Function

```python
from src.tools.indicators import calculate

results = calculate(
    formulas: List[str],           # DSL formula strings
    data: pd.DataFrame,            # OHLCV data
    history_df: Optional[pd.DataFrame] = None  # Historical context
) -> Dict[str, pd.Series]
```

### Example

```python
import pandas as pd
from src.tools.indicators import calculate

# Load data
data = pd.read_csv("AAPL.csv")

# Calculate single indicator
rsi = calculate(["rsi_14"], data)
print(rsi["rsi_14"])

# Calculate multiple indicators
results = calculate(["rsi_14", "ema_20", "sma_50", "bb_20_2"], data)
print(results.keys())

# With historical lookback
results = calculate(
    ["macd_12_26_9"],
    data,
    history_df=historical_data
)
```

## Formula DSL - Simplified Condition Syntax

### Overview

Write clear, readable conditions in strategy configs:

**Before (Traditional):**
```python
data['close'] > data['ema_20'] and data['ema_20'] > data['ema_50'] and data['adx_14'] > 25
```

**After (DSL):**
```python
close[0] > ema_20[0] and ema_20[0] > ema_50[0] and adx_14[0] > 25
```

### Syntax Reference

| Syntax | Meaning | Example | Expands To |
|--------|---------|---------|-----------|
| `indicator[0]` | Current bar | `close[0]` | `data['close']` |
| `indicator[-1]` | Previous bar | `ema_20[-1]` | `data.shift(1)['ema_20']` |
| `indicator[-2]` | 2 bars back | `rsi_14[-2]` | `data.shift(2)['rsi_14']` |
| `indicator[n]` | n bars back | `atr_14[-5]` | `data.shift(5)['atr_14']` |

### Examples

```yaml
# Simple condition
buy_conditions: close[0] > ema_20[0]

# Multiple conditions (AND)
buy_conditions: close[0] > ema_20[0] and ema_20[0] > ema_50[0] and rsi_14[0] > 40

# Historical comparison
buy_conditions: sha_10_green[0] == 1 and sha_10_red[-1] == 1

# Trend strength
buy_conditions: close[0] > ema_20[0] and adx_14[0] > adx_14[-1]

# Complex logic
buy_conditions: |
  (close[0] > ema_20[0] and ema_20[0] > ema_50[0]) and
  (rsi_14[0] > 40 and rsi_14[0] < 80) and
  (adx_14[0] > 25)

# Color indicators (binary)
buy_conditions: sha_10_green[0] == 1 and sha_10_red[-1] == 1 and ema_20[0] < close[0]
```

### Operators

| Operator | Use | Example |
|----------|-----|---------|
| `>` | Greater than | `close[0] > 100` |
| `<` | Less than | `close[0] < ema_20[0]` |
| `==` | Equal | `sha_10_green[0] == 1` |
| `>=` | Greater or equal | `adx_14[0] >= 25` |
| `<=` | Less or equal | `rsi_14[0] <= 70` |
| `and` | Both true | `close[0] > 100 and rsi_14[0] > 50` |
| `or` | Either true | `close[0] > 100 or rsi_14[0] > 80` |
| `not` | Negate | `not (close[0] < 100)` |

### Usage in Strategy Config

```yaml
name: my_strategy
universe: etf_pea

indicators:
  - close
  - ema_20
  - ema_50
  - rsi_14
  - adx_14
  - sha_10

# In buy conditions
buy_conditions: |
  close[0] > ema_20[0] and 
  ema_20[0] > ema_50[0] and 
  rsi_14[0] > 40

# In sell conditions
sell_conditions: |
  close[0] < ema_20[0] or 
  rsi_14[0] < 30

# In signals configuration
signals:
  parameters:
    trend:
      formula: |
        close[0] > ema_20[0] and 
        ema_20[0] > ema_50[0] and 
        adx_14[0] > 25

# In watchlist configuration
watchlist:
  parameters:
    trend:
      formula: close[0] > ema_20[0] and adx_14[0] > 20
```

### Backward Compatibility

The old `data['...']` syntax still works! Mix both syntaxes if needed:

```python
close[0] > data['ema_20'] and data['rsi_14'] > 50
```

Both will be automatically converted to the same internal representation.

## DSL Syntax Reference

### Momentum Indicators

| Formula | Returns | Range | Description |
|---------|---------|-------|-------------|
| `rsi_14` | RSI value | 0-100 | Relative Strength Index, period 14 |
| `rsi_7` | RSI value | 0-100 | Fast RSI, period 7 |
| `rsi_21` | RSI value | 0-100 | Slow RSI, period 21 |
| `macd_12_26_9` | Dict: macd, signal, histogram | n/a | MACD with fast=12, slow=26, signal=9 |
| `macd` | Dict: macd, signal, histogram | n/a | MACD with defaults |
| `roc_12` | Rate of change % | -100 to +∞ | Rate of Change, 12-period |
| `roc_5` | Rate of change % | -100 to +∞ | Fast ROC, 5-period |

### Trend Indicators

| Formula | Returns | Range | Description |
|---------|---------|-------|-------------|
| `ema_20` | EMA value | n/a | Exponential Moving Average, 20-period |
| `ema_5` | EMA value | n/a | Fast EMA, 5-period |
| `ema_50` | EMA value | n/a | Medium EMA, 50-period |
| `ema_200` | EMA value | n/a | Slow EMA, 200-period |
| `sma_50` | SMA value | n/a | Simple Moving Average, 50-period |
| `sma_200` | SMA value | n/a | Long-term SMA, 200-period |
| `adx_14` | ADX value | 0-100 | Average Directional Index, 14-period |

### Volatility Indicators

| Formula | Returns | Range | Description |
|---------|---------|-------|-------------|
| `atr_14` | ATR value | n/a | Average True Range, 14-period |
| `bb_20_2` | Dict: upper, middle, lower | n/a | Bollinger Bands, period 20, std dev 2 |
| `bb_20_3` | Dict: upper, middle, lower | n/a | Wider bands, period 20, std dev 3 |
| `parkinson_14` | Volatility | n/a | Parkinson Volatility Estimator, 14-period |
| `rs_14` | Volatility | n/a | Rogers-Satchell Volatility, 14-period |

### Volume Indicators

| Formula | Returns | Range | Description |
|---------|---------|-------|-------------|
| `obv` | OBV value | n/a | On-Balance Volume |
| `mfi_14` | Money Flow Index | 0-100 | Money Flow Index, 14-period |
| `cmf_20` | Chaikin Money Flow | -1 to +1 | Chaikin Money Flow, 20-period |
| `vratio_20` | Volume Ratio | 0 to +∞ | Volume Ratio, 20-period |

### Support/Resistance Indicators

| Formula | Returns | Range | Description |
|---------|---------|-------|-------------|
| `support_14` | Level | n/a | Support level, 14-period lookback |
| `resistance_14` | Level | n/a | Resistance level, 14-period lookback |
| `pivot_classic` | Dict: R2, R1, P, S1, S2 | n/a | Classic Pivot Points |
| `pivot_camarilla` | Dict: R4-R1, P, S1-S4 | n/a | Camarilla Pivot Points |

### Change Indicators

| Formula | Returns | Range | Description |
|---------|---------|-------|-------------|
| `chgpct_1` | Percentage change | -100 to +∞ | Percentage change, 1-period |
| `chgpct_5` | Percentage change | -100 to +∞ | 5-period percentage change |
| `chglog_1` | Log change | n/a | Log returns, 1-period |

## Complete Examples

### Example 1: Basic Momentum Strategy

```python
data = pd.read_csv("stock_data.csv")

# Get momentum indicators
results = calculate([
    "rsi_14",        # Overbought/oversold
    "macd_12_26_9",  # Trend confirmation
    "roc_12"         # Momentum strength
], data)

# Use indicators
rsi = results["rsi_14"]
macd = results["macd_12_26_9"]
roc = results["roc_12"]

# Generate signals
buy_signal = (rsi < 30) & (macd > 0)
sell_signal = (rsi > 70) & (macd < 0)
```

### Example 2: Trend Following

```python
# Get trend indicators
results = calculate([
    "ema_20",
    "sma_50",
    "adx_14"
], data)

ema = results["ema_20"]
sma = results["sma_50"]
adx = results["adx_14"]

# Generate signals
uptrend = (ema > sma) & (adx > 25)
downtrend = (ema < sma) & (adx > 25)
```

### Example 3: Volatility Breakout

```python
# Get volatility indicators
results = calculate([
    "bb_20_2",      # Bollinger Bands
    "atr_14",       # Average True Range
    "vratio_20"     # Volume Ratio
], data)

bb = results["bb_20_2"]
atr = results["atr_14"]
vol_ratio = results["vratio_20"]

# Generate signals
breakout = (data["Close"] > bb["bb_upper"]) & (vol_ratio > 1.2)
```

### Example 4: Backtesting with History

```python
# Load data
all_data = pd.read_csv("full_history.csv")
backtest_start = 500

# For each day, calculate with history context
for i in range(backtest_start, len(all_data)):
    current_data = all_data.iloc[i:i+1]
    historical_data = all_data.iloc[:i]
    
    results = calculate(
        ["ema_50", "rsi_14"],
        current_data,
        history_df=historical_data
    )
    
    ema = results["ema_50"].iloc[-1]
    rsi = results["rsi_14"].iloc[-1]
    # ... trading logic
```

## Error Handling

```python
from src.tools.finance.indicators import (
    InvalidFormulaError,
    ColumnError,
    InsufficientDataError,
    IndicatorNotFoundError
)

try:
    results = calculate(["rsi_14"], data)
except InvalidFormulaError as e:
    print(f"Invalid formula: {e}")
except ColumnError as e:
    print(f"Missing column: {e}")
except InsufficientDataError as e:
    print(f"Insufficient data: {e}")
except IndicatorNotFoundError as e:
    print(f"Indicator not implemented: {e}")
```

## Available Indicators

### Quick Reference

```
Momentum:     rsi_N  macd_F_S_G  roc_N
Trend:        ema_N  sma_N       adx_N
Volatility:   atr_N  bb_N_S      parkinson_N  rs_N
Volume:       obv    mfi_N       cmf_N        vratio_N
Support:      support_N  resistance_N  pivot_method
Change:       chgpct_N  chglog_N

Where: N=number, F/S/G=MACD params, S=std dev, method=classic|camarilla|woodie|demark
```

## Parameter Naming Convention

Since the DSL uses underscores to separate parameters, compound indicator names must avoid underscores:

| Avoid | Use Instead | Reason |
|-------|-------------|--------|
| `volume_ratio_20` | `vratio_20` | Underscore reserved for params |
| `bollinger_bands_20_2` | `bb_20_2` | Short names without underscores |
| `change_pct_1` | `chgpct_1` | Avoid multi-word names |
| `rogers_satchell_14` | `rs_14` | Use abbreviations |

## Performance Notes

- **Selective calculation**: Only requested indicators computed
- **History context**: Avoids redundant data loading in loops
- **Series format**: NumPy-backed for fast calculations
- **Memory efficient**: Dict return for multi-value indicators

## Migration Guide

### From Old DSL

**Old:**
```python
from src.lib.finance.indicators.dsl.engine import eval_expression
result = eval_expression("rsi_14", data)
```

**New:**
```python
from src.tools.finance.indicators import calculate
results = calculate(["rsi_14"], data)
result = results["rsi_14"]
```

## Troubleshooting

### "Invalid formula syntax"
- Check spelling of indicator name
- Verify parameters are numeric and in correct order
- Use short, underscore-free names

### "Column missing"
- Data must have OPEN, HIGH, LOW, CLOSE, VOLUME columns
- Check column names are uppercase

### "Insufficient data"
- Some indicators need minimum lookback (e.g., 50+ rows for SMA_50)
- Provide more historical data

### "Too many parameters"
- Formula uses compound names with underscores
- Use abbreviated names: `vratio` not `volume_ratio`, `rs` not `rogers_satchell`


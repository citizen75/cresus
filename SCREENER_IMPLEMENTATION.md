# Screener Implementation - Complete Execution Pipeline

## Overview

The screener now has full execution capability. When you run `cresus screener run <screener_name>`, it:

1. **Loads tickers** from a universe or explicit ticker list
2. **Fetches historical data** for each ticker using `DataHistory`
3. **Calculates indicators** specified in the screener configuration
4. **Evaluates the DSL formula** on historical data
5. **Outputs matching rows** with OHLCV data and all calculated indicators

## Architecture

### Data Flow

```
Screener Config
    ↓
Load Tickers (from Universe or explicit list)
    ↓
For each ticker:
    ├─ Load historical OHLCV data (DataHistory)
    ├─ Calculate indicators (indicators.calculate)
    ├─ Evaluate formula (dsl_parser.evaluate_dsl_vectorized)
    └─ Collect matching rows
    ↓
Save Results (CSV with OHLCV + all indicators)
    ↓
Display summary and top 10 matches
```

### Key Components

#### 1. ScreenerManager.run()
**File**: `src/tools/screener/__init__.py`

Orchestrates the entire screening workflow:
- Validates screener exists
- Gets tickers from source (Universe) or explicit list
- Processes each ticker through the screening pipeline
- Saves results with proper metadata

```python
success, message, result_id = manager.run("screener_name")
```

**Returns**: `(success: bool, message: str, result_id: Optional[str])`

#### 2. Data Loading
**Class**: `tools.data.core.DataHistory`

```python
dh = DataHistory("AAPL")
df = dh.get_all()  # Returns pd.DataFrame with OHLCV
```

**Columns**: timestamp, open, high, low, close, volume, ...

#### 3. Indicator Calculation  
**Function**: `tools.indicators.calculate()`

```python
results = calculate(
    ["rsi_14", "ema_20", "sha_10_up"],
    history_df
)
# Returns dict of indicator_name -> pd.Series
```

#### 4. Formula Evaluation
**Function**: `tools.formula.dsl_parser.evaluate_dsl_vectorized()`

Evaluates DSL formulas like `sha_10_up[0]==1` on entire DataFrame:

```python
matches = evaluate_dsl_vectorized(
    "sha_10_up[0] == 1 and close[0] > ema_20[0]",
    history_df
)
# Returns pd.Series of booleans
```

**DSL Syntax**:
- `indicator[0]` - Current bar value
- `indicator[-1]` - Previous bar (1 bar back)
- `indicator[-n]` - n bars back
- Operators: `==`, `!=`, `<`, `>`, `<=`, `>=`, `&&` (and), `||` (or)
- Logic: `!` (not)

## Usage Examples

### Command Line

```bash
# Run a screener
cresus screener run etf_pea_ha_up

# View results
cresus screener results etf_pea_ha_up

# Show specific result
cresus screener result-show etf_pea_ha_up 20260529_104421_eb6346e7
```

### Python API

```python
from src.tools.screener import ScreenerManager

manager = ScreenerManager()
success, message, result_id = manager.run("momentum")

if success:
    results = manager.get_result("momentum", result_id)
    print(f"Found {len(results)} matches")
    for row in results[:10]:
        print(f"{row['date']} {row['ticker']} {row['close']}")
```

## Screener Configuration Format

```yaml
# ~/.cresus/db/screeners/my_screener/screener.yml
name: my_screener
source: cac40                           # Universe name
# OR:
tickers:                                # Explicit tickers
  - AAPL
  - MSFT

indicators:                             # Required indicators
  - rsi_14
  - ema_20
  - sha_10_up

formula: "sha_10_up[0] == 1"            # DSL formula to evaluate

description: "Find stocks with uptrend"

actions: {}                              # Future: notifications, etc.
```

## Example: Real Screener

The `etf_pea_ha_up` screener finds ETF PEA stocks where SHA-10 shows uptrend:

```yaml
name: etf_pea_ha_up
source: cac40
indicators:
  - sha_10_up
formula: sha_10_up[0] == 1
```

**Result**: 26,889 matches (one for each bar where SHA-10 indicates uptrend)

## Output Format

Results are saved as CSV with columns:

| Column | Type | Example |
|--------|------|---------|
| date | ISO datetime | 2026-05-29 14:30:00 |
| ticker | string | AAPL |
| open | float | 150.25 |
| high | float | 151.50 |
| low | float | 149.80 |
| close | float | 150.75 |
| volume | float | 45000000 |
| rsi_14 | float | 65.4 |
| ema_20 | float | 149.20 |
| ... | ... | ... |

## Performance Considerations

### Optimization Strategies

1. **Indicator Caching**: Indicators are calculated once per ticker using vectorized operations
2. **Formula Vectorization**: DSL evaluation uses pandas.eval for all rows at once (not row-by-row)
3. **Data Sorting**: Historical data is sorted ascending (oldest first) for proper lookback
4. **Error Resilience**: Skips tickers with missing data or calculation failures

### Typical Performance

- **Small universe (5 tickers)**: ~1-2 seconds
- **Medium universe (40 tickers, CAC40)**: ~5-10 seconds  
- **Large universe (100+ tickers)**: ~30-60 seconds

Depends on:
- Historical data depth (years of OHLCV)
- Number of indicators to calculate
- Formula complexity

## Error Handling

The screener is fault-tolerant:
- **Missing ticker data** → Skipped (doesn't fail entire run)
- **Indicator calculation failure** → Ticker skipped
- **Formula syntax error** → Entire screener fails with message
- **Universe not found** → Screener fails gracefully

## Integration Points

### Dependencies

```
ScreenerManager
├─ tools.universe.Universe (get_tickers)
├─ tools.data.core.DataHistory (get_all)
├─ tools.indicators.calculate (compute indicators)
└─ tools.formula.dsl_parser.evaluate_dsl_vectorized (evaluate formula)
```

### CLI Integration

The refactored CLI command `ScreenerCommand` calls:

```python
success, message, result_id = manager.run(screener_name)
# Displays results in formatted table
```

## Test Coverage

**Unit tests**: `tests/cli/test_screener_command.py`
- Screener command routing
- Result save/load
- Error handling
- Integration workflows

**Integration**: Manual testing via CLI
```bash
cresus screener run etf_pea_ha_up
```

## Future Enhancements

1. **Parallel Processing**: Process multiple tickers in parallel
2. **Result Filtering**: Filter results by date range, ticker pattern
3. **Notifications**: Alert on matches (email, Slack, etc.)
4. **Backtesting**: Calculate P&L on screener signals
5. **Performance Ranking**: Rank screeners by hit rate
6. **Custom Actions**: Trigger trades, orders, etc. on matches

## Technical Notes

### Column Name Normalization

The implementation handles:
- Lowercase indicator names in formulas (`sha_10_up[0]`)
- Mixed case in OHLCV data (`Open`, `High`, `Low`, `Close`, `Volume`)
- Automatic lowercase conversion for consistency

### DataFrame Sorting

Historical data must be sorted ascending (oldest first) for:
- Proper lookback window calculation
- Formula evaluation with shift indices (`indicator[-n]`)
- Correct time series relationships

The implementation automatically ensures proper sorting:
```python
history_df = history_df.sort_values('timestamp').reset_index(drop=True)
```

### Formula Evaluation Pipeline

1. **Tokenization**: Formula → Tokens (lexer)
2. **Parsing**: Tokens → AST (parser)
3. **Evaluation**: AST → Boolean series (evaluator)
4. **Vectorization**: Pandas operations on entire DataFrame

This provides:
- Type safety via DSL parsing
- Performance via vectorized operations
- Readability via domain-specific syntax

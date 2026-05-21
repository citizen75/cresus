# Indicator Checker

Comprehensive validation tool for technical indicators to identify errors, warnings, and potential issues.

## Quick Start

### Check a Single Indicator

```python
from src.tools.indicators import check_indicator

# Simple check
result = check_indicator('rsi_14', verbose=False)
print(f"Valid: {result.is_valid()}")
print(f"Errors: {result.errors}")
print(f"Warnings: {result.warnings}")

# Detailed output
check_indicator('rsi_14', verbose=True)
```

### Check Multiple Indicators

```python
from src.tools.indicators import check_indicator

# Check multiple indicators at once
results = check_indicator(['rsi_14', 'ema_20', 'bb_20_2'], verbose=True)

# Access individual results
for name, result in results.items():
    if not result.is_valid():
        print(f"❌ {name}: {result.errors}")
```

### Check All Registered Indicators

```python
from src.tools.indicators import check_all_indicators

# Check every registered indicator
results = check_all_indicators(verbose=True)

# Get summary
valid_count = sum(1 for r in results.values() if r.is_valid())
print(f"Valid indicators: {valid_count}/{len(results)}")
```

### Print Reports

```python
from src.tools.indicators import check_indicator, print_checker_report

# Check and print detailed report
result = check_indicator('macd_12_26_9', verbose=False)
print_checker_report(result)

# Or multiple indicators
results = check_indicator(['rsi_14', 'ema_20'], verbose=False)
print_checker_report(results)
```

## Check Results

### CheckResult Object

```python
from src.tools.indicators import CheckResult

result = check_indicator('rsi_14', verbose=False)

# Properties
result.indicator_name     # Name of the indicator checked
result.exists             # Whether indicator was found in registry
result.syntax_valid       # Whether module loaded successfully
result.errors             # List of errors (critical issues)
result.warnings           # List of warnings (non-critical issues)
result.infos              # List of informational messages
result.test_results       # Dict of test execution metrics

# Methods
result.is_valid()         # Returns True if no critical errors
result.add_error(msg)     # Add an error message
result.add_warning(msg)   # Add a warning message
result.add_info(msg)      # Add an info message
result.summary()          # Get one-line summary
```

## What Gets Checked

### 1. Registry Lookup
- ✓ Indicator exists in registry
- ✓ Tries full name first (e.g., 'rsi_14'), then base name (e.g., 'rsi')

### 2. Module Loading
- ✓ Function is importable
- ✓ No import errors

### 3. Function Signature
- ✓ Has 'data' or 'df' parameter
- ✓ Inspects all parameters

### 4. Sample Data Testing
- ✓ Runs with generated OHLCV data
- ✓ Checks output type (Series or Dict)
- ✓ Detects NaN values (warns if > 50%)
- ✓ Detects infinity values (error)
- ✓ Validates output length

### 5. Code Quality Checks
- ✓ Detects bare 'except:' clauses
- ✓ Detects print() statements
- ✓ Finds TODO/FIXME comments
- ✓ Identifies hardcoded parameters

## Sample Output

### Valid Indicator
```
============================================================
Indicator: rsi_14
============================================================
✅ rsi_14: OK

ℹ️  Info (4):
   • Indicator module loaded successfully
   • Function signature: (data: pandas.DataFrame, period: int = 14, history_df: Optional[pandas.DataFrame] = None, **kwargs) -> pandas.Series
   • Sample data test passed
   • Possible hardcoded numeric parameters found

📊 Test Results:
   • output_type: Series
   • series_length: 100
   • nan_count: 0
   • inf_count: 0
```

### Multiple Indicators Summary
```
============================================================
Checking 4 indicator(s)
============================================================

✅ bb_20_2: OK
✅ ema_20: OK
❌ invalid_test: Indicator not found
✅ rsi_14: OK

============================================================
Summary: 3 valid, 1 errors, 0 warnings
============================================================
```

## Error Levels

- **Critical**: Indicator won't load or execute (syntax errors, import failures)
- **Error**: Indicator fails on valid data (NaN/Inf issues, test failures)
- **Warning**: Indicator works but has issues (high NaN count, code quality)
- **Info**: Informational messages (parameter detection, successful tests)

## Integration Examples

### Check indicators in tests
```python
from src.tools.indicators import check_indicator

def test_my_indicator():
    result = check_indicator('custom_indicator', verbose=False)
    assert result.is_valid(), f"Indicator has issues: {result.errors}"
```

### CLI usage (future)
```bash
# Check single indicator
python -m src.tools.indicators.checker rsi_14

# Check multiple
python -m src.tools.indicators.checker rsi_14 ema_20 bb_20_2

# Check all
python -m src.tools.indicators.checker --all
```

## Implementation Notes

- Sample data uses uppercase column names (OPEN, HIGH, LOW, CLOSE, VOLUME)
- All 26 registered indicators pass validation
- Supports both parametrized names (e.g., 'rsi_14') and base names (e.g., 'rsi')
- Generates synthetic OHLCV data with 100 rows for testing

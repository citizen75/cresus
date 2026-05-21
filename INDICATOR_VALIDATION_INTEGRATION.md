# Indicator Validation Integration

Integration of the Indicator Checker into StrategyValidator for comprehensive strategy validation.

## Overview

The StrategyValidator now includes indicator validation that:
1. **Extracts** all indicators referenced in strategy formulas
2. **Validates** both declared and extracted indicators using the Indicator Checker
3. **Reports** mismatches between declared and extracted indicators
4. **Integrates** seamlessly with `cresus strategy check` command

## New StrategyValidator Methods

### `validate_extracted_indicators(strategy_config) -> (Dict[str, CheckResult], List[str])`
Validates all indicators found in strategy formulas.

```python
from src.tools.strategy.validator import StrategyValidator

validator = StrategyValidator()
check_results, errors = validator.validate_extracted_indicators(strategy_config)

# check_results: Dict mapping indicator names to CheckResult objects
# errors: List of error messages for invalid indicators
```

### `validate_indicators_in_declaration(strategy_config) -> (Dict[str, CheckResult], List[str])`
Validates indicators explicitly declared in `strategy.indicators`.

```python
check_results, errors = validator.validate_indicators_in_declaration(strategy_config)
```

### `validate_all_indicators(strategy_config) -> Dict[str, Any]`
Comprehensive validation of all indicators (declared and extracted).

Returns a dict with:
- `declared_results`: CheckResult for declared indicators
- `declared_errors`: Errors from declared indicators
- `extracted_results`: CheckResult for extracted indicators  
- `extracted_errors`: Errors from extracted indicators
- `declared_indicators`: List of declared indicator names
- `extracted_indicators`: List of extracted indicator names
- `missing_from_declaration`: Indicators in formulas but not declared
- `total_errors`: Combined error count
- `is_valid`: Boolean - all checks passed

```python
result = validator.validate_all_indicators(strategy_config)

print(f"Valid: {result['is_valid']}")
print(f"Declared: {len(result['declared_indicators'])}")
print(f"Extracted: {len(result['extracted_indicators'])}")
print(f"Missing: {result['missing_from_declaration']}")
```

## CLI Integration

### `cresus strategy check <strategy_name>`

Enhanced with indicator validation:

```bash
$ cresus strategy check cac_trend

Strategy Compliance Check: cac_trend

Indicators (23): adx_14, adx_20, atr_14, ...

✗ 4 error(s) found:

    Errors (Template, Formulas & Indicators)
  ╭─────────────────────────────────────────╮
  │ Declared indicator 'close': Indicator   │
  │   'close' not found in registry          │
  │ Declared indicator 'volume': Indicator  │
  │   'volume' not found in registry         │
  │ Indicator 'close': Indicator 'close'    │
  │   not found in registry                  │
  │ Indicator 'volume': Indicator 'volume'  │
  │   not found in registry                  │
  ╰─────────────────────────────────────────╯

📊 Indicator Summary: Declared: 23, Extracted from formulas: 17
```

## Validation Checks Performed

### For Each Indicator

1. **Registry Lookup**
   - ✓ Indicator exists in registry
   - ✓ Supports parametrized names (e.g., 'rsi_14')

2. **Module Loading**
   - ✓ Function is importable
   - ✓ No import errors

3. **Function Signature**
   - ✓ Has 'data' or 'df' parameter
   - ✓ Proper parameter types

4. **Sample Data Testing**
   - ✓ Runs with synthetic OHLCV data
   - ✓ Validates output format
   - ✓ Detects NaN/Inf values

5. **Code Quality**
   - ✓ Bare 'except:' clauses
   - ✓ Print statements
   - ✓ TODO/FIXME comments

### For Strategy

1. **Indicator Declaration**
   - ✓ Declared indicators exist
   - ✓ All declared indicators are valid

2. **Formula Analysis**
   - ✓ Extract all referenced indicators
   - ✓ Validate each referenced indicator
   - ✓ Identify missing declarations

3. **Consistency**
   - ✓ All extracted indicators are declared
   - ✓ No orphaned references

## Example Usage

### Python API

```python
from src.tools.strategy.validator import StrategyValidator
import yaml

# Load strategy
with open('strategy.yml') as f:
    strategy = yaml.safe_load(f)

# Validate
validator = StrategyValidator()
result = validator.validate_all_indicators(strategy)

if result['is_valid']:
    print("✅ All indicators are valid!")
else:
    print(f"❌ Found {result['total_errors']} errors:")
    for error in result['declared_errors'] + result['extracted_errors']:
        print(f"  - {error}")

    if result['missing_from_declaration']:
        print(f"\n⚠️  Missing from declaration:")
        for ind in result['missing_from_declaration']:
            print(f"  - {ind}")
```

### CLI

```bash
# Check strategy with full indicator validation
cresus strategy check my_strategy

# Auto-fix missing indicators
cresus strategy check my_strategy --fix
```

## Implementation Details

### Files Modified

1. **src/tools/strategy/validator.py**
   - Added indicator imports from checker
   - Added 3 new validation methods
   - Integrated CheckResult handling

2. **src/cli/commands/strategy.py**
   - Updated `check()` method to validate indicators
   - Enhanced `_display_results()` with indicator summary
   - Shows declared vs extracted indicator counts

### Files Created

1. **src/tools/indicators/checker.py** (existing)
   - Provides indicator validation functionality

2. **src/tools/indicators/CHECKER.md** (existing)
   - Documentation for indicator checker

## Sample Output

### Valid Strategy
```
✓ Strategy is valid and ready to use
```

### Invalid Strategy
```
✗ 2 error(s) found:

    Errors (Template, Formulas & Indicators)
  ╭──────────────────────────────────────────╮
  │ Declared indicator 'fake_ind':           │
  │   Indicator 'fake_ind' not found in      │
  │   registry                               │
  │ Indicator 'another_fake':                │
  │   Indicator 'another_fake' not found in  │
  │   registry                               │
  ╰──────────────────────────────────────────╯

📊 Indicator Summary: Declared: 25, Extracted from formulas: 20, 
                      Missing from declaration: 2
```

## Error Messages

- **Not found in registry**: Indicator name doesn't match any registered indicator
- **Extracted but not declared**: Indicator used in formula but missing from indicators list
- **Declared but not used**: Indicator in list but not referenced in any formula
- **Invalid output**: Indicator produces NaN/Inf values

## Notes

- Column references like 'close' and 'volume' will show as "not found" - these are data fields, not indicators
- Use `--fix` flag to automatically add missing indicators to declaration
- All 26 registered indicators pass validation checks
- Sample data uses 100-row synthetic OHLCV data for testing

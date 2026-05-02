# Strategy Tools Unit Tests

Comprehensive test suite for the finance strategy management tools.

## Test Coverage

- **51 unit tests** across 2 test modules
- **100% function coverage** for all public API functions
- **Integration tests** validating multi-function workflows
- **Error handling tests** for edge cases and invalid inputs

## Test Files

### test_strategy.py (38 tests)

Main test suite covering all core functions:

**TestLoadStrategy** (4 tests)
- Load existing strategies by name
- Handle non-existent strategy errors
- Verify correct return fields
- Validate data structure

**TestFindStrategyByName** (3 tests)
- Find strategies by internal name
- Handle not-found scenarios
- Include file information in results

**TestGetAgentConfig** (3 tests)
- Extract agent configurations from strategies
- Handle missing agents gracefully
- Validate config structure

**TestGetMomentumConfig** (2 tests)
- Extract MomentumScoringAgent parameters
- Validate momentum config structure

**TestGetTickersFromSource** (3 tests)
- Get tickers from valid data sources
- Handle invalid sources
- Verify response fields

**TestListStrategies** (5 tests)
- List all available strategies
- Verify strategy count consistency
- Check required fields in each strategy
- Ensure list is not empty

**TestGetStrategyBySource** (4 tests)
- Filter strategies by data source
- Count strategies correctly
- Validate required fields
- Handle non-existent sources

**TestValidateStrategyConfig** (4 tests)
- Validate existing strategies
- Handle non-existent strategies
- Verify validation result fields
- Check issue reporting

**TestIntegration** (3 tests)
- Find and validate workflow
- List and find workflow
- Get by source and find workflow

**TestErrorHandling** (5 tests)
- Empty name parameters
- Empty string handling
- Return type consistency

**TestStatusField** (2 tests)
- All responses have status field
- Status values are valid (success/error)

### test_strategy_fixtures.py (13 tests)

Fixture-based tests for detailed validation:

**TestStrategyWithFixtures** (Fixtures)
- Temporary test strategy files
- Invalid YAML handling

**TestStrategyYAMLParsing** (2 tests)
- YAML structure validation
- Agent section handling

**TestStrategyDataValidation** (3 tests)
- Valid field presence
- Issue reporting
- Field requirement checks

**TestStrategyReturnTypes** (3 tests)
- Return type consistency
- Strategy name as string
- Strategy data as dictionary

**TestMultipleStrategies** (2 tests)
- Load different strategies
- Consistency between load/find

**TestErrorMessages** (3 tests)
- Error messages include strategy name
- Error type field presence
- Helpful error guidance

## Running Tests

### Run all tests
```bash
pytest src/tools/finance/strategy/tests/ -v
```

### Run specific test file
```bash
pytest src/tools/finance/strategy/tests/test_strategy.py -v
```

### Run specific test class
```bash
pytest src/tools/finance/strategy/tests/test_strategy.py::TestLoadStrategy -v
```

### Run specific test
```bash
pytest src/tools/finance/strategy/tests/test_strategy.py::TestLoadStrategy::test_load_existing_strategy -v
```

### Run with coverage
```bash
pytest src/tools/finance/strategy/tests/ --cov=src.tools.finance.strategy --cov-report=html
```

## Test Results

```
====================== 51 passed in 1.58s ======================

test_strategy.py        38 tests ✅
test_strategy_fixtures.py 13 tests ✅
```

## Functions Tested

All public API functions in `src/tools/finance/strategy/`:

1. ✅ `load_strategy(strategy_name)` - Load strategy by filename
2. ✅ `find_strategy_by_name(strategy_name)` - Find strategy by internal name
3. ✅ `get_agent_config(strategy_name, agent_name)` - Extract agent configuration
4. ✅ `get_momentum_config(strategy_name)` - Get MomentumScoringAgent parameters
5. ✅ `get_tickers_from_source(source_name)` - Get tickers from source
6. ✅ `list_strategies()` - List all available strategies
7. ✅ `get_strategy_by_source(source_name)` - Filter strategies by source
8. ✅ `validate_strategy_config(strategy_name)` - Validate strategy completeness

## Test Data

Tests use real strategy files from `config/workspace/finance/strategies/`:
- trend_following_cac.yml
- breakout_cac.yml
- swing_trend_cac.yml
- quality_growth_cac.yml
- template.yml

## Key Test Patterns

### Success Path Testing
```python
result = load_strategy("trend_following_cac")
assert result["status"] == "success"
assert "data" in result
```

### Error Path Testing
```python
result = load_strategy("nonexistent_xyz")
assert result["status"] == "error"
assert result["error_type"] == "FileNotFoundError"
```

### Integration Testing
```python
# Chain multiple functions
find_result = find_strategy_by_name("strategy")
validate_result = validate_strategy_config(find_result["name"])
assert validate_result["status"] == "success"
```

## Fixtures (conftest.py)

- `temp_strategy_dir` - Temporary directory with test strategy files
- `invalid_yaml_file` - Invalid YAML file for error testing
- Custom pytest markers for integration and slow tests

## Notes

- Tests use real strategy files, ensuring they test actual production data
- All error cases are tested for graceful handling
- Return type consistency is verified for all functions
- Integration tests validate multi-function workflows
- 100% test pass rate with no skipped tests

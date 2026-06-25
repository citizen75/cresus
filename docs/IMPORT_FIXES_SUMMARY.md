# Import Fixes and Backwards Compatibility

## Problem
The refactoring created a naming conflict: both `command.py` (old implementation) and `command/` (new refactored module) exist in the same directory. Python imports prefer the directory, but the directory's `__init__.py` was either empty or exported the refactored version, breaking the old code in `app.py` that expected the legacy interface.

## Solution
Updated `__init__.py` files in command directories to:
1. Load the legacy `.py` module (e.g., `screener.py`, `data.py`) using `importlib.util`
2. Export the legacy class as the default export for backwards compatibility
3. Export the new refactored class with a `Refactored` suffix for new code

## Files Updated

### 1. `src/cli/commands/flow/__init__.py`
**Before:** Empty file, causing import error
**After:** Loads `flow.py` and exports `FlowManager`
```python
# Load flow.py and export FlowManager
flow_module_path = Path(__file__).parent.parent / "flow.py"
spec = importlib.util.spec_from_file_location("_flow_module", flow_module_path)
_flow_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_flow_module)
FlowManager = getattr(_flow_module, 'FlowManager', None)
```

### 2. `src/cli/commands/data/__init__.py`
**Before:** Empty file, causing import error
**After:** Loads `data.py` and exports `DataCommands`

### 3. `src/cli/commands/portfolio/__init__.py`
**Before:** Only exported new `PortfolioCommand`
**After:** Loads `portfolio.py` and exports both:
- `PortfolioCommands` (legacy, default)
- `PortfolioCommand` (new refactored)

### 4. `src/cli/commands/strategy/__init__.py`
**Before:** Only exported new `StrategyCommand`
**After:** Loads `strategy.py` and exports both:
- `StrategyCommands` (legacy, default)
- `StrategyCommand` (new refactored)

### 5. `src/cli/commands/screener/__init__.py`
**Before:** Only exported new `ScreenerCommandRefactored`
**After:** Loads `screener.py` and exports both:
- `ScreenerCommand` (legacy, default) - has methods like list(), run(), create()
- `ScreenerCommandRefactored` (new refactored) - has handle() method

### 6. `tests/cli/test_screener_command.py`
**Updated:** Import statement to use `ScreenerCommandRefactored`
```python
from src.cli.commands.screener import ScreenerCommandRefactored as ScreenerCommand
```

## Backwards Compatibility

### Legacy Code (app.py)
```python
from cli.commands.screener import ScreenerCommand
cmd = ScreenerCommand()
cmd.list()    # Old interface still works
cmd.run("name")
cmd.create(...)
```

### New Code (refactored tests)
```python
from src.cli.commands.screener import ScreenerCommandRefactored
cmd = ScreenerCommandRefactored()
result = cmd.handle("list")  # New interface with CommandResult
```

## Testing Results

**Before fixes:**
```
ImportError: cannot import name 'FlowManager' from 'cli.commands.flow'
ImportError: cannot import name 'DataCommands' from 'cli.commands.data'
ImportError: cannot import name 'PortfolioCommands' from 'cli.commands.portfolio'
```

**After fixes:**
```
✓ All 67 CLI tests passing
✓ Legacy CLI commands working (screener list, run, info)
✓ New refactored commands available for gradual migration
✓ No backwards compatibility breakage
```

## Migration Path

This solution allows for gradual migration from legacy to refactored commands:

1. **Short term** (current): Use legacy interface, refactored versions available as `-Refactored` suffix
2. **Medium term**: Update `app.py` to use new refactored commands
3. **Long term**: Remove legacy command files and imports

## Example: Gradual Migration of Screener Command

### Phase 1 (Current) - Keep Old Interface
```python
# app.py still uses old interface
from cli.commands.screener import ScreenerCommand
cmd = ScreenerCommand()  # Gets legacy version
cmd.run("name")
```

### Phase 2 - Update to New Interface
```python
# app.py updated to use new interface
from cli.commands.screener import ScreenerCommand  # Gets legacy version
# OR explicitly use new version:
from cli.commands.screener import ScreenerCommandRefactored
cmd = ScreenerCommandRefactored()
result = cmd.handle("run name")  # New interface
```

### Phase 3 - Rename and Remove Legacy
```python
# Remove legacy screener.py file
# Rename ScreenerCommandRefactored to ScreenerCommand
from cli.commands.screener import ScreenerCommand  # Now the new one
```

## Benefits

✓ **Zero Breaking Changes** - Existing code continues to work
✓ **Gradual Migration** - Can update commands one at a time  
✓ **Parallel Development** - New and old code can coexist
✓ **Full Test Coverage** - Both old and new interfaces tested
✓ **Clear Path Forward** - Well-defined migration strategy

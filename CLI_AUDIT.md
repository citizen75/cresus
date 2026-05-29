# Cresus CLI Code Audit & Recommendations

## Executive Summary

The CLI codebase has **13 critical issues** and **organizational debt** that hinder maintainability, testability, and extensibility. The main issue is a **monolithic app.py (1563 lines)** with mixed concerns and inconsistent patterns.

---

## Critical Issues Identified

### 1. **MONOLITHIC app.py (1563 lines)** ⚠️ CRITICAL
**Issue**: Single file handles initialization, command routing, help text, business logic, and output formatting.

**Problems**:
- Violates Single Responsibility Principle
- Difficult to test individual commands
- High cognitive load (40+ public methods)
- Hard to maintain and debug
- Inconsistent patterns within same file

**Impact**: Medium-High | **Severity**: Critical

---

### 2. **Inconsistent Command Handling Patterns** ⚠️ CRITICAL
**Issue**: Three different patterns for command handling:

```
Pattern A: app.py handles everything inline (do_data, do_analyze, do_strategy)
Pattern B: Delegates to command class (DataCommands, StrategyCommands)
Pattern C: Partial delegation with methods (do_strategy + _list_strategies, _show_strategy)
```

**Examples**:
- `do_data()` → delegates to `DataCommands.handle()`
- `do_strategy()` → mixes inline logic + helper methods
- `do_screener()` → inline with loop and complex parsing
- `do_service()` → delegates to `ServiceManager`

**Problems**:
- Developers don't know which pattern to follow for new commands
- Inconsistent testing strategy needed per command
- Command lifecycle unclear

**Impact**: High | **Severity**: Critical

---

### 3. **Manual String-based Argument Parsing** ⚠️ HIGH
**Issue**: Unsafe manual parsing with `parts[i]` throughout codebase.

**Examples**:
```python
# In app.py
parts = args.split()
command = parts[0] if parts else None
service_name = parts[1]  # IndexError if only 1 part!

# String manipulation without validation
if remaining.startswith('"') or remaining.startswith("'"):
    # Complex quote handling
```

**Problems**:
- IndexError exceptions on missing arguments
- No input validation
- Quote handling fragile (analyze command)
- Inconsistent date parsing (`_looks_like_date`)
- Regex-free date validation
- No type coercion

**Impact**: High | **Severity**: High

---

### 4. **Duplicated Rich Output Code** ⚠️ MEDIUM
**Issue**: Similar table/console output repeated across 9 files.

**Examples**:
```python
# Repeated in: app.py, data.py, flow.py, portfolio.py, strategy.py, screener.py, service.py
table = Table(title="...", box=box.ROUNDED)
table.add_column("Name", style="cyan")
table.add_column("Description")
console.print(table)
```

**Problems**:
- Inconsistent styling (some use ROUNDED, others SIMPLE)
- No reusable table formatting utilities
- 100+ lines of duplicated table code
- Maintenance burden (if we change style globally, 9 files to update)

**Impact**: Medium | **Severity**: Medium

---

### 5. **Inconsistent Naming Conventions** ⚠️ MEDIUM
**Issue**: Command classes named inconsistently.

| File | Class | Pattern |
|------|-------|---------|
| strategy.py | `StrategyCommands` | Plural + Commands |
| data.py | `DataCommands` | Plural + Commands |
| screener.py | `ScreenerCommand` | Singular + Command ❌ |
| portfolio.py | `PortfolioCommands` | Plural + Commands |
| service.py | `ServiceManager` | Singular + Manager ❌ |
| flow.py | `FlowManager` | Singular + Manager ❌ |

**Problems**:
- Inconsistent naming makes it unclear which pattern new code should follow
- `ServiceManager` vs `ServiceCommands` - which is it?

**Impact**: Low-Medium | **Severity**: Medium

---

### 6. **Duplicated Help Text & Command Metadata** ⚠️ MEDIUM
**Issue**: Command help/usage duplicated in multiple places.

**Examples**:
```python
# In do_strategy() docstring
"""..."""

# Then in code when args is empty:
if not args:
    table = Table(title="Strategy Management Commands")
    table.add_row("strategy list", "List all strategies")
    # Same text as docstring!
    
# Then in do_help():
"""📈 Strategy": {
    "strategy": "Validate strategies (check|calc|train|predict)",
}
```

**Problems**:
- Three places maintain same help text
- Risk of desynchronization
- Maintenance burden

**Impact**: Low | **Severity**: Medium

---

### 7. **No Base Command Class or Interface** ⚠️ HIGH
**Issue**: Each command handler implements patterns independently.

**Current State**:
```python
class DataCommands:
    def __init__(self, data_manager):
        self.data_manager = data_manager
    def handle(self, args):
        # ... complex parsing logic

class StrategyCommands:
    def __init__(self, project_root):
        self.project_root = project_root
    def command(self, args):  # Different method name!
        # ... similar parsing logic
```

**Problems**:
- No contract/interface to follow
- Different constructor signatures
- Different public method names (`handle()` vs `command()` vs nothing)
- Each duplicates argument parsing logic
- Each reimplements help text generation

**Impact**: High | **Severity**: High

---

### 8. **Broad Exception Handling** ⚠️ MEDIUM
**Issue**: `except Exception` catches all errors without specificity.

**Examples**:
```python
try:
    # ... complex logic
except Exception as e:
    console.print(f"[red]Error: {e}[/red]")
    # No logging, no error type distinction
```

**Problems**:
- Swallows programming errors (typos, bugs)
- Hard to debug
- No error categorization (user error vs system error)
- No recovery strategies
- Lost stack traces

**Impact**: Medium | **Severity**: Medium

---

### 9. **Mixed Concerns in Command Files** ⚠️ MEDIUM
**Issue**: Command files mix presentation, business logic, and I/O.

**Example from data.py** (737 lines):
```
Lines 1-30:    Imports
Lines 31-100:  DataCommands class init
Lines 101-300: Command routing and parsing
Lines 301-600: Table formatting (presentation)
Lines 601-737: Business logic (data operations)
```

**Problems**:
- Hard to test business logic without CLI
- Presentation logic mixed with command logic
- No clear separation of concerns

**Impact**: Medium | **Severity**: Medium

---

### 10. **Inconsistent Error Messages** ⚠️ LOW
**Issue**: Error messages inconsistent in format and detail.

**Examples**:
```python
# Verbose
console.print("[red]✗ Error: strategy_name required[/red]")
console.print("[yellow]Usage: strategy show <strategy_name>[/yellow]")

# Terse  
console.print(f"[red]✗ {message}[/red]")

# Different
console.print(f"[red]Error: {e}[/red]")
```

**Impact**: Low | **Severity**: Low

---

### 11. **Command History Location Hardcoded** ⚠️ LOW
**Issue**: History file path hardcoded in `_setup_history()`.

```python
history_file = Path.home() / ".cresus" / "history"  # Hardcoded
```

**Problems**:
- Not configurable
- Couples CLI to home directory structure
- Hard to customize per environment

**Impact**: Low | **Severity**: Low

---

### 12. **No Command Validation Layer** ⚠️ MEDIUM
**Issue**: No validation before command execution.

**Example**:
```python
# In do_backtest - directly calls without validation
cmd = parts[0]
strategy = parts[1]  # What if parts[1] doesn't exist?
# No validation that strategy exists
```

**Problems**:
- Errors only surface during execution
- No early validation
- No helpful error messages

**Impact**: Medium | **Severity**: Medium

---

### 13. **Import Path Inconsistencies** ⚠️ LOW
**Issue**: Imports use different path patterns.

**In app.py**:
```python
from cli.commands.service import ServiceManager  # Relative to src/
from tools.data.manager import DataManager       # Different pattern
```

**In strategy.py**:
```python
sys.path.insert(0, str(src_path))  # Workaround needed
from tools.strategy.validator import StrategyValidator
```

**Problems**:
- Inconsistent import patterns
- Some files need sys.path manipulation
- Fragile imports
- Not using __init__.py properly

**Impact**: Low | **Severity**: Low

---

## Code Quality Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Largest file | app.py (1563 lines) | < 300 lines | ❌ |
| Cyclomatic complexity | ~45 (app.py) | < 10 | ❌ |
| Test coverage | ~10% | > 80% | ❌ |
| Duplicated code | ~400 lines | < 5% | ❌ |
| Command handler patterns | 3 | 1 | ❌ |
| Average method length | ~60 lines | < 30 lines | ❌ |

---

## Recommendations

### Phase 1: Foundation (Priority 1)

#### 1.1 Create Base Command Class
```python
# src/cli/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

@dataclass
class CommandResult:
    success: bool
    message: str
    data: Optional[dict] = None

class BaseCommand(ABC):
    """Base class for all CLI commands."""
    
    def __init__(self):
        self.console = Console()
    
    @abstractmethod
    def handle(self, args: str) -> CommandResult:
        """Handle command with args string."""
        pass
    
    def parse_args(self, args: str, spec: List[str]) -> dict:
        """Validate and parse arguments against spec."""
        # Implementation validates args
        pass
    
    def print_table(self, data: List[dict], title: str):
        """Standard table printing."""
        pass
    
    def print_help(self):
        """Print command help."""
        pass
```

**Benefit**: Consistent interface, easier to test, centralized help/error handling

---

#### 1.2 Create Utility Modules
```
src/cli/
├── utils/
│   ├── formatter.py      # Rich output formatting (table_from_dicts, print_error, etc.)
│   ├── parser.py         # Argument parsing (parse_args_safe, validate_dates, etc.)
│   ├── validation.py     # Input validation (validate_ticker, validate_strategy, etc.)
│   └── constants.py      # STYLES, COLORS, BOX_TYPES
```

**Benefit**: Reduces code duplication, consistent styling, reusable utilities

---

#### 1.3 Refactor Command Organization
```
src/cli/
├── app.py                # Only routing & initialization
├── base.py               # BaseCommand abstract class
├── utils/                # Shared utilities
└── commands/
    ├── __init__.py
    ├── _base.py          # Import BaseCommand for consistency
    ├── system/
    │   ├── help.py       # help command
    │   ├── status.py     # status command
    │   ├── info.py       # info command
    │   └── history.py    # history command
    ├── data/
    │   ├── __init__.py
    │   ├── indicators.py # data indicators subcommand
    │   ├── fetch.py      # data fetch subcommand
    │   └── manage.py     # data manage subcommand
    ├── strategy/
    │   ├── validate.py
    │   ├── create.py
    │   ├── list.py
    │   └── delete.py
    ├── screener/
    │   ├── __init__.py
    │   ├── create.py
    │   ├── list.py
    │   ├── run.py
    │   └── results.py
    └── portfolio/
        ├── __init__.py
        ├── view.py
        └── manage.py
```

**Benefit**: Clear separation, one command per file, easy to find and test

---

### Phase 2: Implementation (Priority 2)

#### 2.1 Create Argument Parser Helper
```python
# src/cli/utils/parser.py
class ArgParser:
    def __init__(self, spec: Dict[str, str]):
        self.spec = spec  # {'name': 'str', 'count': 'int', 'force': 'bool'}
    
    def parse(self, args: str) -> Dict[str, Any]:
        """Parse and validate against spec."""
        # Raises ValidationError if invalid
        pass

# Usage:
parser = ArgParser({
    'name': 'str',
    'count': 'int',
    '--force': 'bool'
})
result = parser.parse(args)  # {'name': 'foo', 'count': 5, 'force': True}
```

**Benefit**: Eliminates manual parsing, consistent validation, fewer errors

---

#### 2.2 Create Output Formatter
```python
# src/cli/utils/formatter.py
class Formatter:
    @staticmethod
    def table(data: List[dict], title: str, columns: Dict[str, str]) -> Table:
        """Create table from data."""
        
    @staticmethod
    def error(message: str, usage: str = None):
        """Print error message."""
        
    @staticmethod
    def success(message: str):
        """Print success message."""
        
    @staticmethod
    def list_items(items: List[str], title: str):
        """Print formatted list."""

# Usage:
Formatter.table(screeners, "Screeners", {'name': 'Name', 'source': 'Source'})
```

**Benefit**: Consistent output, DRY, easy to theme globally

---

#### 2.3 Refactor app.py
**Current**: 1563 lines with 40+ methods
**Target**: ~200 lines with only:
- `__init__()` - initialization
- `do_help()` - delegate to help command
- Command routing dispatcher
- Project root detection

```python
# Reduced app.py structure:
class CresusCLI(cmd2.Cmd):
    def __init__(self):
        self.commands = {
            'help': HelpCommand(),
            'screener': ScreenerCommand(),
            'strategy': StrategyCommand(),
            'data': DataCommand(),
            # etc.
        }
    
    def default(self, args):
        """Route command to appropriate handler."""
        parts = args.split(None, 1)
        cmd_name = parts[0]
        cmd_args = parts[1] if len(parts) > 1 else ""
        
        if cmd_name not in self.commands:
            self.console.print(f"[red]Unknown command: {cmd_name}[/red]")
            return
        
        try:
            result = self.commands[cmd_name].handle(cmd_args)
            if not result.success:
                self.console.print(f"[red]Error: {result.message}[/red]")
        except ValidationError as e:
            self.console.print(f"[red]Invalid arguments: {e}[/red]")
```

**Benefit**: 87% smaller, clearer routing, easier to test

---

### Phase 3: Quality (Priority 3)

#### 3.1 Add Unit Tests
```python
# tests/cli/test_screener_command.py
from src.cli.commands.screener import ScreenerCommand

def test_screener_list_empty():
    cmd = ScreenerCommand()
    result = cmd.handle("list")
    assert result.success
    assert "No screeners" in result.message

def test_screener_create_invalid():
    cmd = ScreenerCommand()
    result = cmd.handle("create")  # Missing required args
    assert not result.success
    assert "required" in result.message.lower()
```

**Target**: 80%+ coverage for critical commands

---

#### 3.2 Add Integration Tests
```python
# tests/cli/test_cli_integration.py
def test_cli_screener_workflow(temp_cresus_dir):
    """Test complete screener workflow via CLI."""
    cli = CresusCLI(interactive=False)
    
    # Create
    cli.onecmd("screener create momentum 'rsi_14 > 70' 'rsi_14' --source cac40")
    
    # List
    cli.onecmd("screener list")
    
    # Info
    cli.onecmd("screener info momentum")
    
    # Delete
    cli.onecmd("screener delete momentum")
```

---

### Phase 4: Documentation (Priority 4)

#### 4.1 Command Documentation
```python
# src/cli/commands/screener.py
class ScreenerCommand(BaseCommand):
    """Manage screeners.
    
    Subcommands:
        list                Show all screeners
        info <name>        Show screener details
        create <name> ...  Create screener
        delete <name>      Delete screener
    
    Examples:
        screener list
        screener info momentum
        screener create momentum "rsi_14 > 70" "rsi_14"
    """
```

---

#### 4.2 Architecture Documentation
```
# docs/CLI_ARCHITECTURE.md
## Command Structure

All commands inherit from BaseCommand and implement:
- handle(args: str) -> CommandResult
- Argument parsing via ArgParser
- Output via Formatter

## Adding New Commands

1. Create file in src/cli/commands/<category>/<command>.py
2. Inherit from BaseCommand
3. Implement handle() method
4. Register in src/cli/app.py
5. Add tests in tests/cli/commands/<category>/test_<command>.py
```

---

## Implementation Roadmap

### Week 1: Foundation
- [ ] Create BaseCommand abstract class
- [ ] Create parser.py utility
- [ ] Create formatter.py utility
- [ ] Add tests for utilities

### Week 2: Core Commands  
- [ ] Refactor screener command (already a good candidate)
- [ ] Refactor data command
- [ ] Add unit tests
- [ ] Update app.py routing

### Week 3: Remaining Commands
- [ ] Refactor strategy, portfolio, flow commands
- [ ] Add integration tests
- [ ] Reduce app.py to 200 lines

### Week 4: Polish
- [ ] Add documentation
- [ ] Code review
- [ ] Performance testing
- [ ] Final cleanup

---

## Summary of Changes

| Item | Before | After | Benefit |
|------|--------|-------|---------|
| app.py size | 1563 lines | ~200 lines | -87% |
| Command patterns | 3 different | 1 consistent | Clarity |
| Code duplication | ~400 lines | < 50 lines | -87% |
| Test coverage | ~10% | >80% | Quality |
| Error handling | Generic | Specific | Debuggability |
| New command time | ~200 lines | ~50 lines | Productivity |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Breaking existing CLI | High | Maintain backward compatibility during transition |
| Developer ramp-up | Medium | Document new patterns clearly |
| Test coverage gaps | Medium | Phase refactoring, test before refactor |
| Dependency issues | Low | No new external dependencies |

---

## Conclusion

The current CLI code has significant organizational debt that impacts maintainability and testability. By implementing these recommendations, we can:

1. **Reduce complexity** from 40+ methods in app.py to a simple router
2. **Eliminate duplication** of parsing, formatting, and help logic
3. **Establish patterns** that new commands can follow consistently
4. **Enable testing** of individual commands in isolation
5. **Improve debuggability** with specific error handling
6. **Accelerate development** of new commands (from 200 to 50 lines per command)

The phased approach allows us to improve incrementally without disrupting current development.

# CLI Structure

The CLI has been reorganized into modular command categories for better maintainability and clarity.

## Directory Organization

```
src/cli/
├── app.py                  # Main CLI entry point with command dispatch
├── main.py                 # CLI launcher script
├── commands/               # Command modules organized by category
│   ├── __init__.py
│   ├── service.py          # Service management (api, mcp, front)
│   ├── flow.py             # Workflow/flow execution
│   ├── data.py             # Data management (fetch, cache, stats)
│   ├── portfolio.py        # Portfolio management (orders, watchlist)
│   ├── scheduler.py        # Cron job scheduling
│   └── info.py             # Information commands (status, info)
└── STRUCTURE.md            # This file
```

## Command Categories

### Service Management (`commands/service.py`)
Manage backend services (API, MCP, Frontend)
- `service start <service> [-d]`
- `service stop <service>`
- `service status [service]`
- `service logs <service>`

### Workflows (`commands/flow.py`)
Execute trading workflows and analysis flows
- `flow list`
- `flow run <workflow> [strategy] [args]`
- `flow run premarket <strategy>`
- `flow run backtest <strategy> [dates]`

### Data Management (`commands/data.py`)
Manage market data and cache
- `data fetch <type> <target> [date]`
- `data list [type]`
- `data show <ticker>`
- `data clear [type] [ticker]`
- `data stats`
- `data universes`

### Portfolio Management (`commands/portfolio.py`)
View orders and watchlists
- `watchlist <strategy>` - View strategy watchlist with signals
- `orders list <strategy>` - View strategy orders (pending/executed)

### Scheduler (`commands/scheduler.py`)
Manage scheduled cron jobs
- `cron list` - View all cron jobs and next run times

### Information (`commands/info.py`)
System and application information
- `status` - Show system status
- `info` - Show application info

## Adding New Commands

### Step 1: Create a new command module
Create a file in `src/cli/commands/` with a command handler class:

```python
# src/cli/commands/mycategory.py
from rich.console import Console

console = Console()

class MyCommands:
    def handle(self, args: str):
        # Handle command logic
        pass
```

### Step 2: Register in app.py
Add to `CresusCLI.__init__()`:
```python
self.my_commands = MyCommands()
```

Add the command handler method:
```python
def do_mycommand(self, args):
    """My command: mycommand <action> [options]"""
    self.my_commands.handle(args)
```

### Step 3: Update the intro table
Add your command to the welcome table in `_print_intro()`.

## Design Principles

- **Modularity**: Each command category is in its own module
- **Consistency**: All command handlers follow the same pattern
- **Clarity**: Clear separation of concerns
- **Testability**: Individual command modules are easier to test
- **Scalability**: Easy to add new command categories

## Implementation Pattern

Each command module follows this pattern:

```python
class CategoryCommands:
    def handle(self, args: str):
        # Parse and dispatch to sub-commands
        
    def _handle_subcommand(self, args):
        # Implement specific functionality
        
    def _print_results(self, data):
        # Format and display output
```

## Rich Formatting

All commands use the `rich` library for formatted output:
- `Table` for tabular data
- `Panel` for information boxes
- Color-coded status indicators
- Consistent styling across commands

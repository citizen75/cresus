"""Tool-to-function mapping for strategy skill.

Maps tools.json names to Python functions. Includes stub implementations
for unimplemented write operations.
"""

import sys
from pathlib import Path
from typing import Dict, Any
import importlib.util

# Setup path for imports
_script_dir = Path(__file__).parent
_src_path = _script_dir.parent.parent.parent.parent.parent / "src"

# Add paths
for path in [str(_script_dir), str(_src_path)]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Import from strategy module (in same directory)
_spec = importlib.util.spec_from_file_location("strategy", _script_dir / "strategy.py")
_strategy_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_strategy_module)

load_strategy = _strategy_module.load_strategy
list_strategies = _strategy_module.list_strategies
get_strategy_by_source = _strategy_module.get_strategy_by_source
find_strategy_by_name = _strategy_module.find_strategy_by_name
validate_strategy_config = _strategy_module.validate_strategy_config
get_agent_config = _strategy_module.get_agent_config
get_momentum_config = _strategy_module.get_momentum_config

# Stub implementations for unimplemented operations
def _create_strategy(
    strategy_name: str,
    filename: str,
    description: str = "",
    source: str = "",
    config: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Create new strategy configuration file (stub - not yet implemented)."""
    return {
        "status": "error",
        "strategy": strategy_name,
        "message": "create_strategy is not yet implemented. Use the strategy YAML files directly."
    }


def _update_strategy(
    strategy_name: str,
    updates: Dict[str, Any],
) -> Dict[str, Any]:
    """Modify existing strategy configuration (stub - not yet implemented)."""
    return {
        "status": "error",
        "strategy": strategy_name,
        "message": "update_strategy is not yet implemented. Use the strategy YAML files directly."
    }


def _delete_strategy(strategy_name: str) -> Dict[str, Any]:
    """Delete a strategy configuration file (stub - not yet implemented)."""
    return {
        "status": "error",
        "strategy": strategy_name,
        "message": "delete_strategy is not yet implemented. Use the strategy YAML files directly."
    }


def _clone_strategy(
    source_strategy: str,
    new_name: str,
    new_file: str,
) -> Dict[str, Any]:
    """Create new strategy by cloning existing strategy (stub - not yet implemented)."""
    return {
        "status": "error",
        "new_strategy": new_name,
        "source_strategy": source_strategy,
        "message": "clone_strategy is not yet implemented. Use the strategy YAML files directly."
    }


# Tool registry: maps tool name → callable
TOOLS = {
    "load_strategy": load_strategy,
    "list_all_strategies": list_strategies,
    "get_strategies_by_source": get_strategy_by_source,
    "find_strategy_by_name": find_strategy_by_name,
    "validate_strategy_config": validate_strategy_config,
    "get_strategy_agent_config": get_agent_config,
    "get_momentum_scoring_config": get_momentum_config,
    "create_strategy": _create_strategy,
    "update_strategy": _update_strategy,
    "delete_strategy": _delete_strategy,
    "clone_strategy": _clone_strategy,
}

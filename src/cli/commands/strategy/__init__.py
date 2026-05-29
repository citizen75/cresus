"""Strategy command module."""

from .strategy_cmd import StrategyCommand

# Also export legacy StrategyCommands for backwards compatibility
import importlib.util
from pathlib import Path

strategy_module_path = Path(__file__).parent.parent / "strategy.py"
spec = importlib.util.spec_from_file_location("_strategy_module", strategy_module_path)
_strategy_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_strategy_module)

StrategyCommands = getattr(_strategy_module, 'StrategyCommands', None)

__all__ = ["StrategyCommand", "StrategyCommands"]

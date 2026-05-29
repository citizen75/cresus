"""Portfolio command module."""

from .portfolio_cmd import PortfolioCommand

# Also export legacy PortfolioCommands for backwards compatibility
import importlib.util
from pathlib import Path

portfolio_module_path = Path(__file__).parent.parent / "portfolio.py"
spec = importlib.util.spec_from_file_location("_portfolio_module", portfolio_module_path)
_portfolio_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_portfolio_module)

PortfolioCommands = getattr(_portfolio_module, 'PortfolioCommands', None)

__all__ = ["PortfolioCommand", "PortfolioCommands"]

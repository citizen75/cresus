"""CLI command modules organized by category."""

# Refactored commands (Phase 2-3) - these have directories with __init__.py
try:
	from .screener import ScreenerCommand
except ImportError as e:
	ScreenerCommand = None

try:
	from .portfolio import PortfolioCommand
except ImportError as e:
	PortfolioCommand = None

try:
	from .strategy import StrategyCommand
except ImportError as e:
	StrategyCommand = None

__all__ = [
	"ScreenerCommand",
	"PortfolioCommand",
	"StrategyCommand",
]

"""Screener command module."""

# Export the old ScreenerCommand for backwards compatibility with app.py
import importlib.util
from pathlib import Path

# Load the old screener.py module to maintain backwards compatibility
# The old ScreenerCommand has list(), run(), create() etc. methods
screener_module_path = Path(__file__).parent.parent / "screener.py"
spec = importlib.util.spec_from_file_location("_screener_module", screener_module_path)
_screener_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_screener_module)

ScreenerCommand = getattr(_screener_module, 'ScreenerCommand', None)

# Also export the new refactored command as ScreenerCommandRefactored for new code
from .screener_cmd import ScreenerCommand as ScreenerCommandRefactored

__all__ = ["ScreenerCommand", "ScreenerCommandRefactored"]

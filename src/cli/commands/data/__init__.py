"""Data command module."""

import importlib.util
from pathlib import Path

# Load the data.py module from the parent directory
# This handles the naming collision between data.py and data/ directory
data_module_path = Path(__file__).parent.parent / "data.py"
spec = importlib.util.spec_from_file_location("_data_module", data_module_path)
_data_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_data_module)

# Export DataCommands from the loaded module
DataCommands = getattr(_data_module, 'DataCommands', None)

__all__ = ["DataCommands"]

"""Flow command module."""

import importlib.util
from pathlib import Path

# Load the flow.py module from the parent directory
# This handles the naming collision between flow.py and flow/ directory
flow_module_path = Path(__file__).parent.parent / "flow.py"
spec = importlib.util.spec_from_file_location("_flow_module", flow_module_path)
_flow_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_flow_module)

# Export FlowManager from the loaded module
FlowManager = getattr(_flow_module, 'FlowManager', None)

__all__ = ["FlowManager"]

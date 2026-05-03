"""Flow management and execution for CLI."""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add src to path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from flows.watchlist import WatchlistFlow


class FlowManager:
	"""Manager for executing workflow flows."""

	def __init__(self, project_root: Path):
		"""Initialize flow manager.

		Args:
			project_root: Root directory of the project
		"""
		self.project_root = project_root

	def run_workflow(self, workflow_name: str, strategy: str = "default", input_data: Optional[Dict[str, Any]] = None, include_context: bool = False) -> Dict[str, Any]:
		"""Run a workflow.

		Args:
			workflow_name: Name of the workflow to run (e.g., 'watchlist')
			strategy: Strategy name for the workflow
			input_data: Optional input data for the workflow
			include_context: Whether to include flow context in result

		Returns:
			Workflow result dictionary
		"""
		if workflow_name.lower() == "watchlist":
			flow = WatchlistFlow(strategy)

			# Default input if none provided
			if input_data is None:
				input_data = {"tickers": ["AAPL", "GOOGL", "MSFT"]}

			result = flow.process(input_data)

			# Include context if requested
			if include_context:
				result["_context"] = {
					key: value for key, value in flow.context.__dict__.items()
					if not key.startswith("_") and key != "logger"
				}

			return result
		else:
			return {
				"status": "error",
				"message": f"Unknown workflow: {workflow_name}",
				"available": ["watchlist"]
			}

	def list_workflows(self) -> Dict[str, Any]:
		"""List available workflows.

		Returns:
			Dictionary with available workflows
		"""
		return {
			"status": "success",
			"workflows": [
				{
					"name": "watchlist",
					"description": "Stock watchlist generation using strategy analysis",
					"parameters": ["strategy", "tickers"]
				}
			]
		}

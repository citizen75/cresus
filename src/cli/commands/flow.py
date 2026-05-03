"""Flow management and execution for CLI."""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add src to path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from flows.watchlist import WatchlistFlow
from flows.signals import SignalsFlow
from flows.premarket import PreMarketFlow
from tools.strategy.strategy import StrategyManager
from tools.universe.universe import Universe


class FlowManager:
	"""Manager for executing workflow flows."""

	def __init__(self, project_root: Path):
		"""Initialize flow manager.

		Args:
			project_root: Root directory of the project
		"""
		self.project_root = project_root
		self.strategy_manager = StrategyManager(project_root)

	def run_workflow(self, workflow_name: str, strategy: str = "default", input_data: Optional[Dict[str, Any]] = None, include_context: bool = False) -> Dict[str, Any]:
		"""Run a workflow.

		Args:
			workflow_name: Name of the workflow to run (e.g., 'watchlist', 'signals')
			strategy: Strategy name for the workflow
			input_data: Optional input data for the workflow
			include_context: Whether to include flow context in result

		Returns:
			Workflow result dictionary
		"""
		if workflow_name.lower() == "signals":
			# Signals flow - generate trading signals
			flow = SignalsFlow(strategy)
			result = flow.process(input_data or {})

			# Include context if requested
			if include_context:
				result["_context"] = {
					key: value for key, value in flow.context.__dict__.items()
					if not key.startswith("_") and key != "logger"
				}

			return result

		elif workflow_name.lower() == "watchlist":
			# Try to get tickers from input_data or strategy config
			tickers = None

			if input_data and input_data.get("tickers"):
				tickers = input_data["tickers"]
			else:
				# Try to load strategy and extract tickers from universe
				strategy_result = self.strategy_manager.load_strategy(strategy)

				if strategy_result.get("status") != "success":
					return {
						"status": "error",
						"message": f"Strategy '{strategy}' not found. Provide tickers: flow run watchlist {strategy} AAPL GOOGL MSFT"
					}

				# Get universe from strategy
				universe_name = strategy_result.get("source")
				if not universe_name:
					return {
						"status": "error",
						"message": f"Strategy '{strategy}' does not specify a universe or source"
					}

				try:
					universe = Universe(universe_name)
					if not universe.exists():
						return {
							"status": "error",
							"message": f"Universe '{universe_name}' not found"
						}
					tickers = universe.get_tickers()
					if not tickers:
						return {
							"status": "error",
							"message": f"Universe '{universe_name}' is empty"
						}
				except Exception as e:
					return {
						"status": "error",
						"message": f"Failed to load universe '{universe_name}': {str(e)}"
					}

			# Validate tickers
			if not tickers:
				return {
					"status": "error",
					"message": "No tickers found. Provide tickers: flow run watchlist my_strategy AAPL GOOGL MSFT"
				}

			# Prepare input data
			if input_data is None:
				input_data = {}
			input_data["tickers"] = tickers

			flow = WatchlistFlow(strategy)
			result = flow.process(input_data)

			# Include context if requested
			if include_context:
				result["_context"] = {
					key: value for key, value in flow.context.__dict__.items()
					if not key.startswith("_") and key != "logger"
				}

			return result

		elif workflow_name.lower() == "premarket":
			# Pre-market flow - watchlist generation + signal analysis
			flow = PreMarketFlow(strategy)
			result = flow.process(input_data or {})

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
				"available": ["signals", "watchlist", "premarket"]
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
					"name": "signals",
					"description": "Trading signal generation from strategy indicators",
					"parameters": ["strategy"]
				},
				{
					"name": "watchlist",
					"description": "Stock watchlist generation using strategy analysis",
					"parameters": ["strategy", "tickers"]
				},
				{
					"name": "premarket",
					"description": "Pre-market analysis: watchlist generation + signal analysis",
					"parameters": ["strategy"]
				}
			]
		}

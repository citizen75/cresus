"""Watchlist agent for managing stock watchlists."""

from typing import Any, Dict, Optional
from pathlib import Path
from core.agent import Agent
from core.flow import Flow
from agents.data.agent import DataAgent
from agents.watchlist.sub_agents import MaxTickersAgent, FilterVolumeAgent, RankTickersAgent
from tools.strategy.strategy import StrategyManager


class WatchListAgent(Agent):
	"""Agent for managing a watchlist of stocks.

	Orchestrates a multi-step watchlist processing flow using sub-agents.
	Each step reads/modifies the shared context to build the final watchlist.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process watchlist through a series of filtering and ranking steps.

		Creates a Flow with sub-agents that:
		1. Validate tickers from context
		2. Filter by trading volume (from strategy config)
		3. Rank by metric (from strategy config)
		4. Limit to maximum count (from strategy config)
		5. Build final watchlist

		Args:
			input_data: Input data (optional, uses context for tickers)

		Returns:
			Response dictionary with final watchlist
		"""
		if input_data is None:
			input_data = {}

		# Step 1: Get tickers using DataAgent
		data_result = DataAgent(self.name, self.context).process(input_data)
		if data_result['status'] != 'success':
			return {
				'status': 'error',
				'input': input_data,
				'output': {'watchlist': [], 'count': 0},
				'message': data_result['message']
			}

		# Step 2: Load strategy configuration to get watchlist parameters
		strategy_input = self.context.get("strategy_input") or {}
		strategy_name = strategy_input.get("strategy") if isinstance(strategy_input, dict) else None
		if not strategy_name:
			strategy_name = self.context.get("strategy_name")

		watchlist_params = self._get_watchlist_parameters(strategy_name)

		# Step 3: Create a watchlist processing flow with sub-agents
		# The flow uses the same context as this agent
		watchlist_flow = Flow("WatchlistProcessingFlow", context=self.context)

		# Add processing steps with parameters from strategy
		if watchlist_params.get("volume_enabled", True):
			watchlist_flow.add_step(
				FilterVolumeAgent(
					"FilterVolumeStep",
					min_volume=watchlist_params.get("min_volume", 1000000)
				),
				step_name="filter_volume",
				required=False
			)

		if watchlist_params.get("ranking_enabled", True):
			watchlist_flow.add_step(
				RankTickersAgent(
					"RankStep",
					metric=watchlist_params.get("metric", "score")
				),
				step_name="rank_tickers",
				required=False
			)

		if watchlist_params.get("max_enabled", True):
			watchlist_flow.add_step(
				MaxTickersAgent(
					"MaxTickersStep",
					max_tickers=watchlist_params.get("max_count", 50)
				),
				step_name="max_tickers",
				required=False
			)

		# Execute the flow
		flow_result = watchlist_flow.process(input_data)

		# Check flow execution
		if flow_result.get("status") != "success":
			return {
				'status': 'error',
				'input': input_data,
				'output': {'watchlist': [], 'count': 0},
				'message': f"Watchlist flow failed: {flow_result.get('message', 'Unknown error')}"
			}

		# Get final watchlist from context
		watchlist = self.context.get("tickers") or []
		self.context.set("watchlist", watchlist)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"watchlist": watchlist,
				"count": len(watchlist),
				"flow_steps": flow_result.get("steps_completed", 0),
				"parameters": watchlist_params,
			},
		}

	def _get_watchlist_parameters(self, strategy_name: Optional[str] = None) -> Dict[str, Any]:
		"""Get watchlist parameters from strategy configuration.

		Reads watchlist parameters from strategy config file,
		with sensible defaults if not specified.

		Args:
			strategy_name: Name of the strategy to load parameters from

		Returns:
			Dictionary with watchlist parameters
		"""
		# Default parameters
		defaults = {
			"volume_enabled": True,
			"min_volume": 1000000,
			"ranking_enabled": True,
			"metric": "score",
			"max_enabled": True,
			"max_count": 50,
		}

		if not strategy_name:
			return defaults

		try:
			# Load strategy configuration
			from os import environ
			project_root = Path(environ.get("CRESUS_PROJECT_ROOT", "."))
			strategy_manager = StrategyManager(project_root)
			strategy_result = strategy_manager.load_strategy(strategy_name)

			if strategy_result.get("status") != "success":
				return defaults

			strategy_config = strategy_result.get("data", {})
			watchlist_config = strategy_config.get("watchlist", {})

			if not watchlist_config.get("enabled", True):
				# Watchlist is disabled in strategy
				return {**defaults, "volume_enabled": False, "ranking_enabled": False, "max_enabled": False}

			# Extract parameters from strategy config
			params = strategy_config.get("watchlist", {}).get("parameters", {})

			return {
				"volume_enabled": True,
				"min_volume": params.get("volume", {}).get("min_volume", defaults["min_volume"]),
				"ranking_enabled": True,
				"metric": params.get("ranking", {}).get("metric", defaults["metric"]),
				"max_enabled": True,
				"max_count": params.get("tickers", {}).get("max_count", defaults["max_count"]),
			}
		except Exception as e:
			self.logger.warning(f"Failed to load watchlist parameters from strategy: {str(e)}")
			return defaults

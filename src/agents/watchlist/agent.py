"""Watchlist agent for managing stock watchlists."""

from typing import Any, Dict, Optional
from core.agent import Agent
from core.flow import Flow
from agents.data.agent import DataAgent
from agents.watchlist.sub_agents import MaxTickersAgent, FilterVolumeAgent, RankTickersAgent, TrendAgent, VolatilityAgent, FilterStaleDataAgent


class WatchListAgent(Agent):
	"""Agent for managing a watchlist of stocks.

	Orchestrates a multi-step watchlist processing flow using sub-agents.
	Each step reads/modifies the shared context to build the final watchlist.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process watchlist through a series of filtering and ranking steps.

		Creates a Flow with sub-agents that:
		1. Filter out tickers with stale trading data
		2. Filter by trading volume (from strategy config)
		3. Filter by trend
		4. Filter by volatility
		5. Rank by metric (from strategy config)
		6. Limit to maximum count (from strategy config)

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

		# Step 2: Get watchlist parameters from context strategy config
		watchlist_params = self._get_watchlist_parameters()

		# Step 3: Initialize watchlist from tickers
		tickers = self.context.get("tickers") or []
		self.context.set("watchlist", tickers)

		# Step 4: Create a watchlist processing flow with sub-agents
		# The flow uses the same context as this agent
		watchlist_flow = Flow("WatchlistProcessingFlow", context=self.context)

		# Add processing steps with parameters from strategy
		# First step: filter out tickers with stale data (optional for ETF data)
		if watchlist_params.get("stale_data_enabled", False):
			watchlist_flow.add_step(
				FilterStaleDataAgent("FilterStaleDataStep"),
				required=False
			)

		if watchlist_params.get("volume_enabled", True):
			watchlist_flow.add_step(
				FilterVolumeAgent("FilterVolumeStep"),
				required=False
			)

		if watchlist_params.get("trend_enabled", True):
			watchlist_flow.add_step(
				TrendAgent(
					"TrendStep"
				),
				required=False
			)

		if watchlist_params.get("volatility_enabled", True):
			watchlist_flow.add_step(
				VolatilityAgent(
					"VolatilityStep"
				),
				required=False
			)

		if watchlist_params.get("ranking_enabled", True):
			watchlist_flow.add_step(
				RankTickersAgent(
					"RankStep",
					metric=watchlist_params.get("metric", "score")
				),
				required=False
			)

		if watchlist_params.get("max_enabled", True):
			watchlist_flow.add_step(
				MaxTickersAgent(
					"MaxTickersStep",
					max_tickers=watchlist_params.get("max_count", 50)
				),
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
		watchlist = self.context.get("watchlist") or []

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"watchlist": watchlist,
				"count": len(watchlist),
				"flow_steps": flow_result.get("steps_completed", 0),
				"parameters": watchlist_params,
			},
			"execution_history": flow_result.get("execution_history", []),
		}

	def _get_watchlist_parameters(self) -> Dict[str, Any]:
		"""Get watchlist parameters from context strategy configuration.

		Reads watchlist parameters from context.strategy_config which is
		loaded by WatchlistFlow, with sensible defaults if not specified.

		Returns:
			Dictionary with watchlist parameters
		"""
		# Default parameters
		defaults = {
			"volume_enabled": True,
			"trend_enabled": True,
			"volatility_enabled": True,
			"ranking_enabled": True,
			"metric": "score",
			"max_enabled": True,
			"max_count": 50,
		}

		# Get strategy config from context (loaded by WatchlistFlow)
		strategy_config = self.context.get("strategy_config")
		if not strategy_config:
			self.logger.warning("Strategy config not found in context")
			return defaults

		watchlist_config = strategy_config.get("watchlist", {})

		if not watchlist_config.get("enabled", True):
			# Watchlist is disabled in strategy
			return {**defaults, "volume_enabled": False, "trend_enabled": False, "ranking_enabled": False, "max_enabled": False}

		# Extract parameters from strategy config
		params = watchlist_config.get("parameters", {})

		# Check which filters are actually defined in the strategy config
		has_trend = "trend" in params
		has_volatility = "volatility" in params
		has_ranking = "ranking" in params

		return {
			"volume_enabled": "volume" in params,
			"trend_enabled": has_trend,
			"volatility_enabled": has_volatility,
			"ranking_enabled": has_ranking,
			"metric": params.get("ranking", {}).get("metric", defaults["metric"]) if has_ranking else defaults["metric"],
			"max_enabled": True,
			"max_count": params.get("tickers", {}).get("max_count", defaults["max_count"]),
		}

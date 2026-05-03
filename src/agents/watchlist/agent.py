"""Watchlist agent for managing stock watchlists."""

from typing import Any, Dict, Optional
from core.agent import Agent
from core.flow import Flow
from agents.data.agent import DataAgent
from agents.watchlist.sub_agents import MaxTickersAgent, FilterVolumeAgent, RankTickersAgent


class WatchListAgent(Agent):
	"""Agent for managing a watchlist of stocks.

	Orchestrates a multi-step watchlist processing flow using sub-agents.
	Each step reads/modifies the shared context to build the final watchlist.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process watchlist through a series of filtering and ranking steps.

		Creates a Flow with sub-agents that:
		1. Validate tickers from context
		2. Filter by trading volume
		3. Rank by metric
		4. Limit to maximum count
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

		# Step 2: Create a watchlist processing flow with sub-agents
		# The flow uses the same context as this agent
		watchlist_flow = Flow("WatchlistProcessingFlow", context=self.context)

		# Add processing steps
		watchlist_flow.add_step(
			FilterVolumeAgent("FilterVolumeStep", min_volume=1000000),
			step_name="filter_volume",
			required=False
		)
		watchlist_flow.add_step(
			RankTickersAgent("RankStep", metric="score"),
			step_name="rank_tickers",
			required=False
		)
		watchlist_flow.add_step(
			MaxTickersAgent("MaxTickersStep", max_tickers=20),
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
			},
		}

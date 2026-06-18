"""Watchlist filter agent — applies configured filter steps then caps the count."""

from typing import Any, Dict, Optional

from core.agent import Agent
from core.flow import Flow
from agents.watchlist.sub_agents import (
	FilterStaleDataAgent,
	FilterAgent,
	FilterOpenPositionsAgent,
)
from agents.watchlist_filter.sub_agents import MaxTickersAgent


class WatchlistFilterAgent(Agent):
	"""Apply strategy-configured filters to the watchlist, then cap to max_count.

	Designed to run after ranking so MaxTickersAgent keeps the top-N by score,
	not the first-N by insertion order.

	Sub-agents (driven by strategy_config.watchlist.parameters):
	  FilterStaleDataAgent     — drop tickers whose price data is stale
	  FilterAgent              — apply the formula filter expression
	  FilterOpenPositionsAgent — optionally exclude already-open positions
	  MaxTickersAgent          — cap to max_count (always last, after sort)
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		if input_data is None:
			input_data = {}

		watchlist = self.context.get("watchlist")
		if not watchlist:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No watchlist in context",
			}

		params = self._filter_params()

		# Run filter sub-agents
		filter_flow = Flow("WatchlistFilterFlow", context=self.context)
		if params["stale_data_enabled"]:
			filter_flow.add_step(FilterStaleDataAgent("FilterStaleData"), required=False)
		if params["trend_enabled"]:
			filter_flow.add_step(FilterAgent("FilterFormula"), required=True)
		if params["open_positions_enabled"]:
			filter_flow.add_step(FilterOpenPositionsAgent("FilterOpenPositions"), required=False)
		filter_flow.process(input_data)

		# Sort by current ticker_scores["score"] so MaxTickersAgent
		# keeps the top-N by formula score, not by prior LGBM ranking order.
		self._sort_by_score()

		# Cap to max_count
		MaxTickersAgent(
			"MaxTickers",
			max_tickers=params["max_count"],
			context=self.context,
		).run(input_data={})

		watchlist = self.context.get("watchlist") or {}
		self.logger.info(f"[FILTER] {len(watchlist)} tickers (max={params['max_count']})")

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"count": len(watchlist),
				"parameters": params,
			},
		}

	def _sort_by_score(self) -> None:
		"""Sort watchlist dict descending by ticker_scores['score']."""
		watchlist = self.context.get("watchlist") or {}
		ticker_scores = self.context.get("ticker_scores") or {}
		if not watchlist or not ticker_scores:
			return
		sorted_items = sorted(
			watchlist.items(),
			key=lambda x: (ticker_scores.get(x[0]) or {}).get("score", 0),
			reverse=True,
		)
		self.context.set("watchlist", dict(sorted_items))

	def _filter_params(self) -> Dict[str, Any]:
		defaults: Dict[str, Any] = {
			"stale_data_enabled": False,
			"trend_enabled": False,
			"open_positions_enabled": False,
			"max_count": 50,
		}

		strategy_config = self.context.get("strategy_config") or {}
		watchlist_cfg = strategy_config.get("watchlist", {})

		if not watchlist_cfg.get("enabled", True):
			return defaults

		p = watchlist_cfg.get("parameters", {})
		max_count = defaults["max_count"]
		try:
			max_count = int(p.get("tickers", {}).get("max_count", max_count))
		except (ValueError, TypeError):
			pass

		return {
			"stale_data_enabled": p.get("stale_data_enabled", defaults["stale_data_enabled"]),
			"trend_enabled": "filter" in p,
			"open_positions_enabled": p.get("open_positions_enabled", defaults["open_positions_enabled"]),
			"max_count": max_count,
		}

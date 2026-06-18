"""Watchlist agent for managing stock watchlists."""

from typing import Any, Dict, Optional
from core.agent import Agent
from core.flow import Flow
from agents.watchlist.sub_agents import (
	FilterStaleDataAgent,
	FilterAgent,
	FilterOpenPositionsAgent,
	RankTickersAgent,
)


class WatchListAgent(Agent):
	"""Orchestrate the watchlist pipeline: filter then rank.

	Pipeline:
	  1. Initialise watchlist from universe tickers
	  2. FilterStaleDataAgent     — drop stale tickers (if enabled)
	  3. FilterAgent              — apply formula filter (if configured)
	  4. FilterOpenPositionsAgent — exclude open positions (if enabled)
	  5. RankTickersAgent         — sort by ranking metric (if configured)

	Count-capping (max_count) is intentionally excluded here so that ranking
	always sees the full filtered set. WatchlistFilterAgent handles the cap
	after ranking in the outer pipeline.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		if input_data is None:
			input_data = {}

		if not self.context.get("data_history"):
			return {
				"status": "error",
				"input": input_data,
				"output": {"watchlist": [], "count": 0},
				"message": "No data_history in context (DataAgent must run first)",
			}

		tickers = self.context.get("tickers") or []
		self.context.set("watchlist", {t: {} for t in tickers})
		self.logger.debug(f"Initialised watchlist with {len(tickers)} tickers")

		params = self._watchlist_params()
		flow = Flow("WatchlistFlow", context=self.context)

		if params["stale_data_enabled"]:
			flow.add_step(FilterStaleDataAgent("FilterStaleData"), required=False)

		if params["trend_enabled"]:
			flow.add_step(FilterAgent("FilterFormula"), required=True)

		if params["open_positions_enabled"]:
			flow.add_step(FilterOpenPositionsAgent("FilterOpenPositions"), required=False)

		if params["ranking_enabled"]:
			flow.add_step(RankTickersAgent("RankTickers", metric=params["metric"]), required=False)

		flow_result = flow.process(input_data)

		if flow_result.get("status") != "success":
			return {
				"status": "error",
				"input": input_data,
				"output": {"watchlist": [], "count": 0},
				"message": f"Watchlist flow failed: {flow_result.get('message', 'unknown error')}",
			}

		watchlist = self.context.get("watchlist") or {}
		self.logger.info(f"[WATCHLIST] {len(watchlist)} tickers after filter+rank")

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"watchlist": watchlist,
				"count": len(watchlist),
				"flow_steps": flow_result.get("steps_completed", 0),
				"parameters": params,
			},
			"execution_history": flow_result.get("execution_history", []),
		}

	def _watchlist_params(self) -> Dict[str, Any]:
		defaults = {
			"stale_data_enabled": False,
			"trend_enabled": False,
			"open_positions_enabled": False,
			"ranking_enabled": False,
			"metric": "score",
		}

		strategy_config = self.context.get("strategy_config") or {}
		p = strategy_config.get("watchlist", {}).get("parameters", {})

		has_ranking = "ranking" in p
		return {
			"stale_data_enabled": p.get("stale_data_enabled", defaults["stale_data_enabled"]),
			"trend_enabled": "filter" in p,
			"open_positions_enabled": p.get("open_positions_enabled", defaults["open_positions_enabled"]),
			"ranking_enabled": has_ranking,
			"metric": p.get("ranking", {}).get("metric", defaults["metric"]) if has_ranking else defaults["metric"],
		}

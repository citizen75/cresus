"""Market prep agent: unified pre-market pipeline for live bots and backtests.

Consolidates what used to be two diverging pipelines (PreMarketFlow's Flow-based
steps and BotFinance's hand-rolled agent chain) into a single Agent so live bots
and backtests run the exact same logic.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from core.agent import Agent
from agents.strategy.agent import StrategyAgent
from agents.data.agent import DataAgent
from agents.watchlist_alphas.agent import WatchlistAlphasAgent
from agents.watchlist.agent import WatchListAgent
from agents.signals.agent import SignalsAgent
from agents.watchlist_ranking.agent import WatchlistRankingAgent
from agents.watchlist_scoring.agent import WatchlistScoringAgent
from agents.watchlist_sorting.agent import WatchlistSortingAgent
from agents.entry.agent import EntryAgent
from agents.orders_entry.agent import OrdersEntryAgent
from agents.orders_exit.agent import OrdersExitAgent
from agents.orders_sending.agent import OrdersSendingAgent
from agents.watchlist.save_agent import SaveWatchlistAgent


class MarketPrepAgent(Agent):
	"""Pre-market pipeline: data -> watchlist -> ranking -> entry/exit orders -> save.

	Single canonical implementation used by BacktestAgent (backtests), BotFinance
	(live bots) and the premarket CLI/API. Runs each step via _run_sub_agent so a
	non-fatal step failure logs a warning and continues, matching what BotFinance's
	pre-market sequence already tolerated in production.
	"""

	def __init__(self, strategy_name: str, context: Optional[Any] = None):
		super().__init__(f"MarketPrepAgent[{strategy_name}]", context)
		self.strategy_name = strategy_name

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		# Reset per-call: BacktestAgent's day loop calls .process() directly (not .run()),
		# so without this, agents_executed would grow unbounded across simulated days.
		self.agents_executed = []

		flow_input = dict(input_data or {})

		if "portfolio_name" not in flow_input:
			flow_input["portfolio_name"] = self.strategy_name
		self.context.set("portfolio_name", flow_input["portfolio_name"])
		self.context.set("strategy_name", self.strategy_name)

		target_date = flow_input.get("date")
		is_backtest = self.context.get("backtest_id") is not None
		if target_date:
			self.context.set("target_date", target_date)
			# Also set "date" (read by OrdersEntryAgent/OrdersSendingAgent to stamp
			# order created_at/expiration). MarketProcessAgent sets this too during the
			# market phase, but that only happens *after* this pre-market phase runs -
			# on the backtest's very first day, "date" is still unset here, so orders
			# fall back to wall-clock created_at and get a real-world expiration date
			# that never lapses against the simulated timeline, letting them refire.
			self.context.set("date", target_date)

		try:
			self._run_sub_agent(StrategyAgent(f"StrategyAgent[{self.strategy_name}]", self.context), fatal=True)
			self._run_sub_agent(DataAgent(f"DataAgent[{self.strategy_name}]", self.context), fatal=True)
			# Non-fatal: alphas are optional (matches BacktestAgent's own pre-loop setup stance)
			self._run_sub_agent(WatchlistAlphasAgent("WatchlistAlphasAgent", self.context), fatal=False)
			self._run_sub_agent(WatchListAgent("WatchListAgent", self.context), fatal=True)
			self._run_sub_agent(SignalsAgent("SignalsAgent", self.context), fatal=False)
			self._run_sub_agent(WatchlistRankingAgent("WatchlistRankingAgent", self.context), fatal=False)
			self._run_sub_agent(WatchlistScoringAgent("WatchlistScoringAgent", self.context), fatal=False)
			self._run_sub_agent(WatchlistSortingAgent("WatchlistSortingAgent", self.context), fatal=False)

			self._run_sub_agent(EntryAgent("EntryAgent", self.context), fatal=False)
			orders_entry_resp = self._run_sub_agent(OrdersEntryAgent("OrdersEntryAgent", self.context), fatal=False)
			self._run_sub_agent(
				OrdersSendingAgent("OrdersSendingAgentEntry", self.context, orders_key="executable_orders", save=True),
				fatal=False,
			)

			bot_dir = self.context.get("bot_dir")
			save_agent = SaveWatchlistAgent(
				f"SaveWatchlistAgent[{self.strategy_name}]", self.strategy_name,
				context=self.context, bot_dir=bot_dir,
			)
			self._run_sub_agent(save_agent, input_data={"save_enabled": flow_input.get("save_enabled", True)}, fatal=True)

			self._run_sub_agent(OrdersExitAgent("OrdersExitAgent", self.context), fatal=False)
			self._run_sub_agent(
				OrdersSendingAgent("OrdersSendingAgentExit", self.context, orders_key="exit_orders", save=True),
				fatal=False,
			)
		except RuntimeError as e:
			return {"status": "error", "input": flow_input, "output": {}, "message": str(e)}

		# Pre-slice safety net for live mode (backtest mode pre-slices before calling this agent)
		if target_date and not is_backtest:
			data_history = self.context.get("data_history") or {}
			if data_history and not self.context.get("_data_sliced_for_entry"):
				self._set_data_history_for_date(self.context, target_date)
				self.logger.warning(f"Pre-slicing data to {target_date} post-execution (should pre-slice earlier)")
				self.context.set("_data_sliced_for_entry", True)

		result: Dict[str, Any] = {"status": "success", "input": flow_input, "output": {}}

		ranking_scores = self.context.get("ranking_scores") or {}
		result["ranking_scores"] = ranking_scores

		watchlist = self.context.get("watchlist") or []
		result["watchlist"] = watchlist

		result["strategy"] = self.strategy_name

		ticker_scores = self.context.get("ticker_scores") or {}
		result["ticker_scores"] = ticker_scores

		strategy_config = self.context.get("strategy_config") or {}
		indicators = strategy_config.get("indicators", [])
		alpha_names = self.context.get("alpha_names") or []
		result["indicators"] = indicators + alpha_names

		if target_date:
			result["target_date"] = target_date

		orders = orders_entry_resp.get("output", {}).get("orders") or []
		result["orders"] = orders
		result["executable_orders"] = orders
		result["orders_count"] = len(orders)

		self._cleanup_context()

		return result

	def _set_data_history_for_date(self, context: Any, date_str: str) -> None:
		"""Slice data_history to include only data up to a specific date."""
		import pandas as pd
		from datetime import date as date_type

		try:
			target_date = date_type.fromisoformat(date_str)
		except (ValueError, TypeError):
			self.logger.warning(f"Invalid date format: {date_str}, using all available data")
			return

		data_history = context.get("data_history")
		if not data_history:
			return

		sliced_history = {}
		for ticker, df in data_history.items():
			if df.empty:
				sliced_history[ticker] = df
				continue

			if "timestamp" in df.columns:
				timestamps = pd.to_datetime(df["timestamp"])
			else:
				timestamps = pd.to_datetime(df.index)

			dates = timestamps.dt.date
			mask = dates <= target_date
			sliced_history[ticker] = df[mask].copy()

		context.set("data_history", sliced_history)
		self.logger.info(f"Sliced data_history to {date_str} for watchlist analysis")

	def _cleanup_context(self) -> None:
		"""Remove intermediate context variables, keeping only essential ones."""
		to_remove = [
			"signals",
			"entry_scores",
			"timing_scores",
			"rr_metrics",
			"filtered_duplicate_items",
			"sorted_tickers",
			"top_ticker",
			"top_score",
			"_data_sliced_for_entry",
		]

		for var in to_remove:
			if hasattr(self.context, var):
				delattr(self.context, var)
				self.logger.debug(f"Cleaned up context variable: {var}")

	def __repr__(self) -> str:
		return f"MarketPrepAgent(strategy='{self.strategy_name}')"

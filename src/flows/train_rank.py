"""Pre-market flow for generating pre-market signals on watchlist.

Extends Flow to combine watchlist generation with signal analysis.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from core.flow import Flow
from agents.strategy.agent import StrategyAgent
from agents.watchlist.agent import WatchListAgent
from agents.watchlist.save_agent import SaveWatchlistAgent
from agents.watchlist_alphas.agent import WatchlistAlphasAgent
from agents.data.agent import DataAgent
from agents.signals.agent import SignalsAgent
from agents.watchlist_ranking.agent import WatchlistRankingAgent
from agents.entry.agent import EntryAgent
from agents.entry_order.agent import EntryOrderAgent
from agents.exit.agent import ExitAgent


class TrainRankFlow(Flow):
	"""Flow for training and ranking watchlist tickers.

	Generates a watchlist from strategy criteria, then analyzes signals
	on the watchlist tickers for pre-market decision making.
	"""

	def __init__(self, strategy: str, context: Optional[Any] = None):
		"""Initialize pre-market flow with strategy.

		Args:
			strategy: Strategy name to use for watchlist and signals
			context: Optional AgentContext for shared state
		"""
		print(f"Initializing TrainRankFlow for strategy: {strategy}")
		super().__init__(f"TrainRankFlow[{strategy}]", context=context)
		self.strategy_name = strategy
		self._setup_default_steps()

	def _setup_default_steps(self) -> None:
		"""Set up steps for model training flow.

		Flow order:
		1. Strategy - load config and tickers
		2. Data - fetch data and calculate indicators
		3. Ranking (train mode) - train LGBM model with walk-forward validation
		"""
		# Strategy step - load tickers and strategy config
		strategy_agent = StrategyAgent(f"StrategyAgent[{self.strategy_name}]", self.context)
		self.add_step(strategy_agent, step_name="strategy", required=True)

		# Data step - fetch data and calculate indicators for all tickers
		data_agent = DataAgent(f"DataAgent[{self.strategy_name}]", self.context)
		self.add_step(data_agent, step_name="data", required=True)

		# Alphas step - calculate alpha factors from strategy config
		# Adds named alpha columns to data_history for feature engineering
		alphas_agent = WatchlistAlphasAgent("WatchlistAlphasAgent", self.context)
		self.add_step(alphas_agent, step_name="alphas", required=True)
		
		# Ranking step - train LGBM model with walk-forward validation
		ranking_agent = WatchlistRankingAgent("WatchlistRankingAgent", self.context)
		self.add_step(ranking_agent, step_name="ranking", required=True)


	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process training pipeline.

		Trains LGBM model on historical data with walk-forward validation.
		Displays training information at the end.

		Args:
			input_data: Input with strategy_name override

		Returns:
			Training results with model metrics
		"""
		flow_input = input_data or {}
		flow_input["mode"] = "train"  # Set training mode for WatchlistRankingAgent
		flow_input["strategy_name"] = self.strategy_name

		# Set mode in context so all agents can access it
		self.context.set("strategy_name", self.strategy_name)
		self.context.set("ranking_mode", "train")

		# Execute training pipeline
		result = super().process(flow_input)

		# Extract training result from the ranking step
		ranking_step = self.get_step("ranking")
		if ranking_step and ranking_step.get("result"):
			training_result = ranking_step["result"]
			result["output"] = training_result.get("output", {})

		# === DISPLAY TRAINING INFORMATION ===
		self._display_training_info(result)

		return result

	def _display_training_info(self, result: Dict[str, Any]) -> None:
		"""Display training information at the end of flow.

		Shows training metrics like folds, IC, RMSE, model path, etc.

		Args:
			result: Flow result containing training output
		"""
		print("\n" + "="*70)
		print("TRAINING SUMMARY")
		print("="*70)

		output = result.get("output", {})

		# Model training metrics
		folds = output.get("folds", 0)
		metrics = output.get("metrics", {})
		if folds > 0:
			avg_ic = metrics.get("avg_ic")
			avg_rmse = metrics.get("avg_rmse")
			positive_ic_pct = metrics.get("positive_ic_pct")

			print(f"\n📊 Walk-Forward Validation Results:")
			print(f"   Total Folds: {folds}")
			if avg_ic is not None:
				print(f"   Average IC (Spearman): {avg_ic:.4f}")
			if avg_rmse is not None:
				print(f"   Average RMSE: {avg_rmse:.6f}")
			if positive_ic_pct is not None:
				print(f"   Positive IC Folds: {positive_ic_pct:.1f}%")

		# Total samples and features
		total_samples = output.get("samples")
		features = output.get("features")
		if total_samples:
			print(f"\n📈 Dataset Size:")
			print(f"   Total Samples: {total_samples:,}")
			if features:
				print(f"   Features: {features}")

		# Model path
		model_path = output.get("model_path")
		if model_path:
			print(f"\n💾 Model:")
			print(f"   Path: {model_path}")

		print("\n" + "="*70)

	def _set_data_history_for_date(self, context: Any, date_str: str) -> None:
		"""Slice data_history to include only data up to a specific date.

		This allows viewing the watchlist as it was on a specific trading date.

		Args:
			context: AgentContext containing data_history
			date_str: Date string in YYYY-MM-DD format
		"""
		import pandas as pd
		from datetime import date as date_type

		# Parse date string
		try:
			target_date = date_type.fromisoformat(date_str)
		except (ValueError, TypeError):
			self.logger.warning(f"Invalid date format: {date_str}, using all available data")
			return

		data_history = context.get("data_history")
		if not data_history:
			return

		# Slice each ticker's data to target_date and earlier
		sliced_history = {}
		for ticker, df in data_history.items():
			if df.empty:
				sliced_history[ticker] = df
				continue

			# Get timestamp column
			if "timestamp" in df.columns:
				timestamps = pd.to_datetime(df["timestamp"])
			else:
				timestamps = pd.to_datetime(df.index)

			# Extract dates and filter to target_date and earlier
			dates = timestamps.dt.date
			mask = dates <= target_date
			sliced_history[ticker] = df[mask].copy()

		context.set("data_history", sliced_history)
		self.logger.info(f"Sliced data_history to {date_str} for watchlist analysis")

	def _cleanup_context(self) -> None:
		"""Remove intermediate context variables, keeping only essential ones.

		Removes: signals, entry_scores, timing_scores, rr_metrics,
		filtered_duplicate_items, sorted_tickers, etc.

		Keeps: watchlist, data_history, strategy_config, ticker_scores
		(needed for CLI display and downstream flows)

		Note: entry_recommendations is no longer created (watchlist dict now contains all data)
		"""
		# Variables to remove (intermediate calculations not needed in final output)
		to_remove = [
			"signals",  # Signal details (not needed for display)
			"entry_scores",  # Entry signal scores (intermediate)
			"timing_scores",  # Timing analysis scores (intermediate)
			"rr_metrics",  # Risk/reward metrics (intermediate)
			"filtered_duplicate_items",  # Duplicate filter details (intermediate)
			"sorted_tickers",  # Sorted ticker details (superseded by watchlist)
			"top_ticker",  # Top ticker (not critical for final output)
			"top_score",  # Top score (not critical for final output)
			"_data_sliced_for_entry",  # Internal flag
		]

		for var in to_remove:
			if hasattr(self.context, var):
				delattr(self.context, var)
				self.logger.debug(f"Cleaned up context variable: {var}")

	def _strategy_to_portfolio_name(self, strategy_name: str) -> str:
		"""Convert strategy name to portfolio name.

		Uses strategy name directly as portfolio name for consistency with
		portfolio naming conventions (e.g., etf_pea_trend).

		Args:
			strategy_name: Strategy name to convert

		Returns:
			Portfolio name (same as strategy name)
		"""
		return strategy_name

	def __repr__(self) -> str:
		"""String representation of the flow."""
		return f"PreMarketFlow(strategy='{self.strategy_name}', steps={len(self.steps)})"

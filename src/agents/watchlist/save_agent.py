"""Agent to save watchlist with OHLCV and signal data."""

from typing import Any, Dict, Optional
from core.agent import Agent
from tools.watchlist import WatchlistManager


class SaveWatchlistAgent(Agent):
	"""Save watchlist with OHLCV and signal data to disk.

	Reads watchlist, ticker_scores, and data_history from context
	and persists to CSV via WatchlistManager with optional toggle.
	"""

	def __init__(self, name: str = "SaveWatchlistAgent", strategy_name: str = "", context: Optional[Any] = None):
		"""Initialize save watchlist agent.

		Args:
			name: Agent name
			strategy_name: Strategy name for WatchlistManager
			context: Optional AgentContext for shared state
		"""
		super().__init__(name, context)
		self.strategy_name = strategy_name

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Save watchlist with OHLCV and signal data.

		Reads from context:
		- watchlist: List of tickers
		- ticker_scores: Dict of scores and signals
		- data_history: Dict of DataFrames with OHLCV
		- strategy_config: Strategy configuration

		Args:
			input_data: Input data with optional save_enabled toggle

		Returns:
			Response with watchlist save result
		"""
		if input_data is None:
			input_data = {}

		# Get toggle from input data (default: True)
		save_enabled = input_data.get("save_enabled", True)

		# Get data from context
		watchlist = self.context.get("watchlist") or []
		ticker_scores = self.context.get("ticker_scores") or {}
		data_history = self.context.get("data_history") or {}
		strategy_config = self.context.get("strategy_config") or {}

		# Get sorted_tickers from signals if available
		sorted_tickers = self.context.get("sorted_tickers")

		if not ticker_scores:
			return {
				"status": "warning",
				"input": input_data,
				"output": {},
				"message": "No ticker scores to save"
			}

		# Get backtest_dir from context if available (for sandboxed backtesting)
		backtest_dir = self.context.get("backtest_dir") if self.context else None

		# Use WatchlistManager to handle saving
		watchlist_manager = WatchlistManager(self.strategy_name, backtest_dir=backtest_dir)
		save_result = watchlist_manager.process(
			watchlist=watchlist,
			ticker_scores=ticker_scores,
			data_history=data_history,
			sorted_tickers=sorted_tickers,
			strategy_config=strategy_config,
			save_enabled=save_enabled
		)

		return {
			"status": save_result.get("status", "success"),
			"input": input_data,
			"output": save_result,
		}

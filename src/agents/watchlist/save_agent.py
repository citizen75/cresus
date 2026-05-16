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
		"""Save watchlist with OHLCV, signal data, indicators, and order info.

		Reads from context:
		- watchlist: List of tickers
		- ticker_scores: Dict of scores and signals
		- data_history: Dict of DataFrames with OHLCV
		- strategy_config: Strategy configuration
		- entry_recommendations: Entry opportunities with order details
		- entry_scores: Entry scores for analysis

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
		watchlist_dict = self.context.get("watchlist") or {}
		# Convert watchlist dict to list of tickers for WatchlistManager
		watchlist = list(watchlist_dict.keys()) if isinstance(watchlist_dict, dict) else watchlist_dict
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

		# Get portfolio_name from context if available (for portfolio-specific saving)
		portfolio_name = self.context.get("portfolio_name") if self.context else None

		# Collect orders from entry recommendations
		orders = self._extract_orders_from_recommendations()

		# Collect indicators from entry analysis
		indicators = self._extract_indicators_from_context()

		# Use WatchlistManager to handle saving
		# Priority: backtest_dir > portfolio_name > default
		watchlist_manager = WatchlistManager(self.strategy_name, backtest_dir=backtest_dir, portfolio_name=portfolio_name if not backtest_dir else None)
		save_result = watchlist_manager.process(
			watchlist=watchlist,
			ticker_scores=ticker_scores,
			data_history=data_history,
			sorted_tickers=sorted_tickers,
			strategy_config=strategy_config,
			save_enabled=save_enabled,
			orders=orders,
			indicators=indicators,
		)

		return {
			"status": save_result.get("status", "success"),
			"input": input_data,
			"output": save_result,
		}

	def _extract_orders_from_recommendations(self) -> Dict[str, Any]:
		"""Extract order information from watchlist dict.

		Returns:
			Dict mapping ticker -> order info (qty, price, stops, etc.)
		"""
		orders = {}
		watchlist = self.context.get("watchlist") or {}

		for ticker, ticker_data in watchlist.items():
			orders[ticker] = {
				"quantity": ticker_data.get("quantity"),
				"entry_price": ticker_data.get("entry_price"),
				"stop_loss": ticker_data.get("stop_loss"),
				"take_profit": ticker_data.get("take_profit"),
				"execution_method": ticker_data.get("execution_method", "market"),
				"status": "pending",
				"risk_reward": ticker_data.get("risk_reward"),
				"entry_score": ticker_data.get("entry_score"),
			}

		return orders

	def _extract_indicators_from_context(self) -> Dict[str, Dict[str, Any]]:
		"""Extract technical indicators from context with parameter-based names.

		Extracts indicators from both data_history and analysis results.

		Returns:
			Dict mapping ticker -> indicators (rsi_14, atr_14, macd_12_26, etc.)
		"""
		indicators = {}

		# Get data history which contains calculated indicators
		data_history = self.context.get("data_history") or {}

		# Get strategy config for indicator specifications
		strategy_config = self.context.get("strategy_config") or {}
		strategy_indicators = strategy_config.get("indicators", [])

		# Get watchlist (merged dict with all scores)
		watchlist = self.context.get("watchlist") or {}

		# Compile indicators for each ticker
		for ticker in watchlist:
			ticker_indicators = {}
			ticker_data_dict = watchlist[ticker]

			# Extract indicators from data_history if available
			if ticker in data_history:
				ticker_data = data_history[ticker]
				if not ticker_data.empty:
					# Get latest row
					latest = ticker_data.iloc[-1]

					# Add strategy-configured indicators with their parameter names
					for indicator_name in strategy_indicators:
						if indicator_name in latest.index:
							try:
								value = float(latest[indicator_name])
								ticker_indicators[indicator_name] = round(value, 4)
							except (ValueError, TypeError):
								pass

					# Add common technical indicators if present
					common_indicators = {
						'rsi_14': 'rsi_14',
						'rsi_9': 'rsi_9',
						'atr_14': 'atr_14',
						'macd_12_26': 'macd_12_26',
						'ema_10': 'ema_10',
						'ema_20': 'ema_20',
						'sma_5': 'sma_5',
						'sma_20': 'sma_20',
						'adx_20': 'adx_20',
						'volatility_20': 'volatility_20',
					}

					for col_name, indicator_name in common_indicators.items():
						if col_name in latest.index:
							try:
								value = float(latest[col_name])
								if indicator_name not in ticker_indicators:  # Don't override strategy indicators
									ticker_indicators[indicator_name] = round(value, 4)
							except (ValueError, TypeError):
								pass

			# Add analysis metadata from merged watchlist dict
			ticker_indicators["entry_score"] = ticker_data_dict.get("entry_score")
			ticker_indicators["timing_score"] = ticker_data_dict.get("timing_score")
			ticker_indicators["composite_score"] = ticker_data_dict.get("composite_score")

			# Add risk/reward ratio
			rr_ratio = ticker_data_dict.get("rr_ratio")
			if rr_ratio is not None:
				ticker_indicators["rr_ratio"] = round(float(rr_ratio), 4)

			indicators[ticker] = ticker_indicators

		return indicators

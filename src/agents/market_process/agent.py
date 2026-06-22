"""Market process agent: executes pending orders on a specific trading date.

Single canonical implementation used by BacktestAgent (backtests) and BotFinance
(live bots) so both run the exact same order-execution logic. Replaces what used
to be TransactFlow's standalone Flow.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from core.agent import Agent
from agents.trading_broker.agent import TradingBroker
from agents.data.agent import DataAgent
from tools.portfolio.orders import Orders


class MarketProcessAgent(Agent):
	"""Execute pending orders for a portfolio on a given trading date.

	1. Loads market data for the date (live mode only; backtests pre-load it)
	2. Executes pending orders and exits via TradingBroker
	3. Updates portfolio cache

	Results in transactions recorded in the portfolio journal.
	"""

	def __init__(self, context: Optional[Any] = None):
		super().__init__("MarketProcessAgent", context)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute pending orders for a date.

		Args:
			input_data: Input data with:
				- date: Trading date (YYYY-MM-DD or date object) - required
				- portfolio_name: Portfolio to execute for (default: "default")
				- strategy_name: Strategy name (optional, for backtest/bot mode)

		Returns:
			Result dict with execution details (from TradingBroker)
		"""
		# Reset per-call: BacktestAgent's day loop calls .process() directly (not .run()),
		# so without this, agents_executed would grow unbounded across simulated days.
		self.agents_executed = []

		flow_input = input_data or {}

		# Validate date is provided
		date_input = flow_input.get("date")
		if not date_input:
			return {
				"status": "error",
				"message": "date parameter required (YYYY-MM-DD or date object)",
			}

		# Parse and set date in context
		from datetime import datetime
		if isinstance(date_input, str):
			trading_date = datetime.fromisoformat(date_input).date()
		else:
			trading_date = date_input

		portfolio_name = flow_input.get("portfolio_name", "default")
		strategy_name = flow_input.get("strategy_name")

		self.context.set("date", trading_date)
		self.context.set("portfolio_name", portfolio_name)

		# Set strategy_name in context if provided (needed by TradingBroker for take_profit check)
		if strategy_name:
			self.context.set("strategy_name", strategy_name)
			# Load and set strategy_config for exit agents (especially ExitConditionAgent),
			# but skip if already in context (e.g. a bot-local strategy_config loaded from
			# bot_dir/strategy.yml that isn't registered in the centralized StrategyManager)
			if not self.context.get("strategy_config"):
				from tools.strategy import StrategyManager
				sm = StrategyManager()
				strategy_result = sm.load_strategy(strategy_name)
				if strategy_result.get("status") == "success":
					strategy_config = strategy_result.get("data", {})
					self.context.set("strategy_config", strategy_config)
					self.logger.debug(f"Loaded strategy_config for {strategy_name}")

		# Step 1: Get pending orders to determine which tickers to load
		orders_mgr = Orders(portfolio_name, context=self.context.__dict__)
		pending_orders = orders_mgr.get_pending_orders()

		# Step 2: Get pre-sliced day data from BacktestAgent (already organized by date)
		# BacktestAgent creates day_data_cache to avoid filtering on each iteration
		next_day_data = self.context.get("next_day_data") or {}

		# If day data not available (not in backtest), fetch it live so TradingBroker can
		# evaluate limit/stop/target prices against real data instead of {}.
		# data_history is sorted newest-first, so iloc[0] is the latest bar.
		if not next_day_data:
			self._run_sub_agent(DataAgent("DataAgent[market_process]", self.context), fatal=False)
			data_history = self.context.get("data_history") or {}
			next_day_data = {
				ticker: df.iloc[0]
				for ticker, df in data_history.items()
				if df is not None and not df.empty
			}

		# Store day data in context for TradingBroker
		self.context.set("day_data", next_day_data)

		# Step 3: Execute pending orders and exits with day data
		# NOTE: Always run TradingBroker to check for exits, even without pending buy orders
		trading_broker = TradingBroker("TradingBroker", self.context)
		result = trading_broker.process(flow_input)

		return result

	def __repr__(self) -> str:
		return "MarketProcessAgent()"

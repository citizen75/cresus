"""Transaction flow for executing pending orders on a specific date."""

import sys
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import date as date_type

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
	sys.path.insert(0, str(src_path))

from core.flow import Flow
from agents.transact.agent import TransactAgent
from tools.portfolio.orders import Orders


class TransactFlow(Flow):
	"""Flow for executing pending orders on a specific trading date.

	Executes all pending orders for a portfolio on a given date:
	1. Loads market data for the date
	2. Executes pending orders
	3. Updates portfolio cache

	Results in transactions recorded in portfolio journal.
	"""

	def __init__(self, context: Optional[Any] = None):
		"""Initialize transact flow.

		Args:
			context: Optional AgentContext for shared state (e.g., backtest context)
		"""
		super().__init__("TransactFlow", context=context)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute pending orders for a date.

		Args:
			input_data: Input data with:
				- date: Trading date (YYYY-MM-DD or date object) - required
				- portfolio_name: Portfolio to execute for (default: "default")

		Returns:
			Flow result with execution details
		"""
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

		self.context.set("date", trading_date)
		self.context.set("portfolio_name", portfolio_name)

		# Step 1: Get pending orders to determine which tickers to load
		orders_mgr = Orders(portfolio_name, context=self.context.__dict__)
		pending_orders = orders_mgr.get_pending_orders()

		if pending_orders.empty:
			return {
				"status": "success",
				"message": f"No pending orders for {portfolio_name} on {trading_date}",
				"output": {
					"executed": 0,
					"failed": 0,
					"details": [],
				}
			}

		# Step 2: Get pre-sliced day data from BacktestAgent (already organized by date)
		# BacktestAgent creates day_data_cache to avoid filtering on each iteration
		next_day_data = self.context.get("next_day_data") or {}

		# If day data not available (not in backtest), construct minimal day_data
		# This allows TransactFlow to work both in backtest and live scenarios
		if not next_day_data:
			self.logger.warning(f"No pre-loaded day data for {trading_date} - TransactAgent will use available data")

		# Store day data in context for TransactAgent
		self.context.set("day_data", next_day_data)

		# Step 3: Execute pending orders with day data
		transact_agent = TransactAgent("TransactAgent", self.context)
		result = transact_agent.process(flow_input)

		return result

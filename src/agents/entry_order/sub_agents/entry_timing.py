"""Entry timing sub-agent for determining execution methods."""

from typing import Any, Dict, Optional
from core.agent import Agent


class EntryTimingAgent(Agent):
	"""Determine optimal entry execution method.

	Analyzes market conditions and timing signals to select execution
	strategy: market order, limit order, or scale-in approach.
	"""

	def __init__(self, name: str = "EntryTimingAgent"):
		"""Initialize entry timing agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Determine execution method for each order.

		Args:
			input_data: Input data (optional)

		Returns:
			Response with execution timing decisions
		"""
		if input_data is None:
			input_data = {}

		sized_orders = self.context.get("sized_orders") or []

		if not sized_orders:
			return {
				"status": "success",
				"input": input_data,
				"output": {},
				"message": "No sized orders to time"
			}

		timed_orders = []
		for order in sized_orders:
			ticker = order.get("ticker")
			entry_score = self._get_entry_score(ticker)
			momentum = self._get_momentum(ticker)

			# Determine execution method
			if entry_score >= 80 and momentum > 0.5:
				execution_method = "market"
				limit_offset = 0
				scale_count = 1
			elif entry_score >= 65 and momentum > 0:
				execution_method = "limit"
				limit_offset = -0.005  # 0.5% below market
				scale_count = 1
			else:
				execution_method = "scale_in"
				limit_offset = -0.01  # 1% below market
				scale_count = 3  # Scale in over 3 bars

			timed_orders.append({
				"ticker": ticker,
				"shares": order["shares"],
				"entry_price": order["entry_price"],
				"risk_amount": order.get("risk_amount", 0),
				"execution_method": execution_method,
				"limit_offset": limit_offset,
				"scale_count": scale_count,
			})

		self.context.set("timed_orders", timed_orders)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"timed": len(timed_orders),
				"market_orders": len([o for o in timed_orders if o["execution_method"] == "market"]),
				"limit_orders": len([o for o in timed_orders if o["execution_method"] == "limit"]),
				"scale_in": len([o for o in timed_orders if o["execution_method"] == "scale_in"]),
			}
		}

	def _get_entry_score(self, ticker: str) -> float:
		"""Get entry score from context entry recommendations.

		Args:
			ticker: Ticker symbol

		Returns:
			Entry score (0-100)
		"""
		entry_recommendations = self.context.get("entry_recommendations") or []
		for rec in entry_recommendations:
			if rec.get("ticker") == ticker:
				return rec.get("entry_score", 0)
		return 0

	def _get_momentum(self, ticker: str) -> float:
		"""Calculate momentum signal (0-1).

		Args:
			ticker: Ticker symbol

		Returns:
			Momentum value (0-1)
		"""
		# Simplified momentum: based on timing score from entry analysis
		entry_recommendations = self.context.get("entry_recommendations") or []
		for rec in entry_recommendations:
			if rec.get("ticker") == ticker:
				timing_score = rec.get("timing_score", 0)
				return min(timing_score / 100.0, 1.0)
		return 0

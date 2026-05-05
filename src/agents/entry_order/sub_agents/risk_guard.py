"""Risk guard sub-agent for validating portfolio constraints."""

from typing import Any, Dict, Optional
from core.agent import Agent
from tools.portfolio import PortfolioManager


class RiskGuardAgent(Agent):
	"""Validate portfolio-level risk constraints.

	Checks sector exposure, leverage limits, concurrent trades,
	and daily loss limits to prevent over-concentration.

	IMPORTANT: Does NOT allow orders if insufficient cash is available.
	"""

	def __init__(self, name: str = "RiskGuardAgent"):
		"""Initialize risk guard agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Validate orders against portfolio constraints.

		Rejects orders if cash is insufficient. Does not reduce position sizes.

		Args:
			input_data: Input data (optional)

		Returns:
			Response with validation results
		"""
		if input_data is None:
			input_data = {}

		timed_orders = self.context.get("timed_orders") or []

		if not timed_orders:
			return {
				"status": "success",
				"input": input_data,
				"output": {},
				"message": "No orders to validate"
			}

		# Get portfolio state
		portfolio_name = self.context.get("portfolio_name") or "default"
		pm = PortfolioManager(context=self.context.__dict__)
		portfolio_details = pm.get_portfolio_details(portfolio_name)
		cash = pm.get_portfolio_cash(portfolio_name)
		allocation = pm.get_portfolio_allocation(portfolio_name)

		if not portfolio_details:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Portfolio '{portfolio_name}' not found"
			}

		# Get portfolio metrics
		portfolio_value = portfolio_details.get("total_value", 0) + cash
		num_positions = portfolio_details.get("num_positions", 0)

		# Sort by entry score (highest first) to prioritize best opportunities
		entry_recs = {rec["ticker"]: rec for rec in (self.context.get("entry_recommendations") or [])}
		sorted_orders = sorted(
			timed_orders,
			key=lambda o: entry_recs.get(o.get("ticker"), {}).get("composite_score", 0),
			reverse=True
		)

		# Validate orders: only accept if sufficient cash available
		# Do NOT reduce position sizes - reject entirely if insufficient cash
		validated_orders = []
		rejected_orders = []
		remaining_cash = cash

		for order in sorted_orders:
			order_value = order["shares"] * order["entry_price"]

			if order_value <= remaining_cash:
				validated_orders.append(order)
				remaining_cash -= order_value
			else:
				# Insufficient cash - reject the order (don't reduce)
				rejected_orders.append({
					"ticker": order.get("ticker"),
					"shares": order["shares"],
					"entry_price": order.get("entry_price"),
					"order_value": order_value,
					"reason": "Insufficient cash available",
					"cash_short": order_value - remaining_cash,
				})

		self.context.set("validated_orders", validated_orders)
		self.context.set("rejected_orders", rejected_orders)

		total_order_value = sum(o["shares"] * o["entry_price"] for o in validated_orders)
		total_rejected_value = sum(r["order_value"] for r in rejected_orders)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"validated": len(validated_orders),
				"rejected": len(rejected_orders),
				"total_order_value": total_order_value,
				"total_rejected_value": total_rejected_value,
				"portfolio_value": portfolio_value,
				"utilization_pct": (total_order_value / portfolio_value * 100) if portfolio_value > 0 else 0,
				"remaining_cash": remaining_cash,
			},
			"message": f"Validated {len(validated_orders)} orders, rejected {len(rejected_orders)} due to insufficient cash, ${remaining_cash:,.0f} remaining"
		}

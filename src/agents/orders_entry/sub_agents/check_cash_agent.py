"""Agent to validate available cash before order processing."""

from typing import Any, Dict, Optional
from core.agent import Agent
from tools.portfolio.manager import PortfolioManager


class CheckCashAgent(Agent):
	"""Validate available cash against position sizing requirements.

	Checks if available cash is sufficient for the configured position sizing.
	For capital-based sizing, ensures: available_cash > position_size
	For formula-based ordering, evaluates the order condition formula.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Validate available cash.

		Args:
			input_data: Input data (not used, uses context)

		Returns:
			Response with validation result
		"""
		if input_data is None:
			input_data = {}

		portfolio_name = self.context.get("portfolio_name") or "default"
		strategy_config = self.context.get("strategy_config") or {}

		# Get available cash
		pm = PortfolioManager()
		available_cash = pm.get_portfolio_cash(portfolio_name)
		self.logger.debug(f"[CHECK-CASH] Available cash: ${available_cash:.2f}")

		# Check position sizing requirements (from order.parameters.position_sizing)
		order_config = strategy_config.get("order", {})
		order_params = order_config.get("parameters", {})
		position_sizing = order_params.get("position_sizing", {})
		sizing_type = position_sizing.get("type", "")
		sizing_formula = position_sizing.get("formula")

		if sizing_type == "capital" and sizing_formula:
			try:
				required_cash = float(sizing_formula) if isinstance(sizing_formula, (int, float)) else float(sizing_formula)
				if available_cash < required_cash:
					self.logger.warning(f"[CHECK-CASH] Insufficient cash: ${available_cash:.2f} < ${required_cash:.2f}")
					return {
						"status": "exit",
						"input": input_data,
						"output": {
							"available_cash": available_cash,
							"required_cash": required_cash,
						},
						"message": f"Insufficient cash: ${available_cash:.2f} < ${required_cash:.2f}"
					}
			except (ValueError, TypeError) as e:
				self.logger.error(f"[CHECK-CASH] Error parsing position sizing: {e}")
				return {
					"status": "exit",
					"input": input_data,
					"output": {},
					"message": f"Invalid position sizing formula: {sizing_formula}"
				}

		# Check explicit order condition formula
		order_config = strategy_config.get("order", {}).get("parameters", {})
		order_formula = order_config.get("formula")

		if order_formula:
			try:
				from tools.formula.calculator import evaluate
				condition_data = {"available_cash": available_cash}
				should_order = evaluate(order_formula, condition_data)

				if not should_order:
					self.logger.info(f"[CHECK-CASH] Order condition False: '{order_formula}'")
					return {
						"status": "exit",
						"input": input_data,
						"output": {"available_cash": available_cash},
						"message": f"Order condition not met: {order_formula}"
					}
			except Exception as e:
				self.logger.error(f"[CHECK-CASH] Error evaluating order formula: {e}")
				return {
					"status": "exit",
					"input": input_data,
					"output": {},
					"message": f"Error evaluating order formula: {e}"
				}

		# All checks passed
		self.logger.info(f"[CHECK-CASH] Cash validation passed (${available_cash:.2f})")
		return {
			"status": "success",
			"input": input_data,
			"output": {"available_cash": available_cash},
			"message": "Cash validation passed"
		}

"""Exit condition agent — generate SELL orders based on formula evaluation."""

from typing import Any, Dict, List, Optional

from core.agent import Agent
from tools.portfolio.journal import Journal
from tools.formula.calculator import evaluate


class ExitConditionAgent(Agent):
	"""Generate SELL orders for open positions where the exit formula evaluates to True.

	Reads exit formula from:
	    strategy_config.exit.parameters.condition.formula

	When the formula evaluates to True for a position, generates a SELL order
	at the day's close price using the configured order type (default: market).
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		if input_data is None:
			input_data = {}

		strategy_config = self.context.get("strategy_config") or {}
		exit_params = strategy_config.get("exit", {}).get("parameters", {})
		formula = exit_params.get("condition", {}).get("formula")
		order_type = exit_params.get("order_type", "market").lower()

		if not formula or formula.lower() == "false":
			return {
				"status": "success",
				"output": {"exit_orders": []},
				"message": "No exit condition formula configured",
			}

		portfolio_name = self.context.get("portfolio_name") or "default"
		day_data = self.context.get("day_data") or {}
		data_history = self.context.get("data_history") or {}

		journal = Journal(portfolio_name, context=self.context.__dict__)
		exit_orders = self._generate_orders(journal, day_data, data_history, formula, order_type)

		return {
			"status": "success",
			"output": {"exit_orders": exit_orders},
			"message": f"Generated {len(exit_orders)} condition-based SELL order(s)",
		}

	# ------------------------------------------------------------------
	# Private helpers
	# ------------------------------------------------------------------

	def _generate_orders(
		self,
		journal: Journal,
		day_data: Dict[str, Any],
		data_history: Dict[str, Any],
		formula: str,
		order_type: str,
	) -> List[Dict[str, Any]]:
		exit_orders: List[Dict[str, Any]] = []

		open_positions = journal.get_open_positions()
		if open_positions.empty:
			return exit_orders

		for _, position in open_positions.iterrows():
			ticker = str(position.get("ticker", ""))
			quantity = position.get("quantity")
			if quantity is None or float(quantity) <= 0:
				continue

			market_row = day_data.get(ticker)
			if market_row is None:
				continue

			# Prefer full history for DSL shift operators; fall back to single row
			eval_data = data_history.get(ticker, market_row)

			try:
				condition_met = evaluate(formula, eval_data)
			except Exception as e:
				self.logger.error(f"[EXIT-COND] {ticker}: formula error — {e}")
				continue

			if not condition_met:
				continue

			close_price = self._price(market_row, "close")
			if close_price is None or close_price <= 0:
				self.logger.warning(f"[EXIT-COND] {ticker}: invalid close price — skipping")
				continue

			self.logger.info(
				f"[EXIT-COND] {ticker}: condition met → SELL {float(quantity):.0f} @ {close_price:.2f}"
			)
			exit_orders.append({
				"ticker": ticker,
				"quantity": float(quantity),
				"exit_price": close_price,
				"exit_type": "condition",
				"execution_method": order_type,
				"metadata": {
					"formula": formula,
					"reason": "exit_condition_met",
				},
			})

		return exit_orders

	@staticmethod
	def _price(row: Any, field: str) -> Optional[float]:
		try:
			v = row.get(field) if hasattr(row, "get") else None
			return float(v) if v is not None else None
		except (ValueError, TypeError):
			return None

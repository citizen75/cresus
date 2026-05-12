"""Exit condition sub-agent for generating SELL orders based on formula evaluation."""

from typing import Any, Dict, Optional, List
from core.agent import Agent
from tools.portfolio.journal import Journal
from tools.formula.calculator import evaluate


class ExitConditionAgent(Agent):
	"""Generate SELL orders based on condition formula evaluation.

	Checks all open positions against exit condition formula and generates
	SELL orders for any that match the condition (formula evaluates to True).
	Does not execute directly - returns orders for TransactAgent to execute.
	"""

	def __init__(self, name: str = "ExitConditionAgent"):
		"""Initialize exit condition agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Generate condition-based SELL orders for open positions.

		Args:
			input_data: Input data with:
				- portfolio_name: Portfolio to generate orders for
				- day_data: Pre-sliced market data {ticker: row}
				- data_history: Full price history {ticker: DataFrame}

		Returns:
			Response with generated SELL orders
		"""
		if input_data is None:
			input_data = {}

		portfolio_name = self.context.get("portfolio_name") or "default"
		day_data = input_data.get("day_data") or self.context.get("day_data") or {}
		data_history = input_data.get("data_history") or self.context.get("data_history") or {}

		# Get exit condition formula from strategy config
		strategy_config = self.context.get("strategy_config") or {}
		exit_config = strategy_config.get("exit", {}).get("parameters", {})
		exit_condition_formula = exit_config.get("condition", {}).get("formula")

		self.logger.debug(f"Exit condition formula from config: {repr(exit_condition_formula)}")

		if not exit_condition_formula or exit_condition_formula.lower() == "false":
			return {
				"status": "success",
				"output": {"exit_orders": []},
				"message": "No exit condition formula configured",
			}

		journal = Journal(portfolio_name, context=self.context.__dict__)
		exit_orders = self._generate_condition_exit_orders(
			journal, day_data, data_history, exit_condition_formula
		)

		return {
			"status": "success",
			"output": {
				"exit_orders": exit_orders,
			},
			"message": f"Generated {len(exit_orders)} condition-based SELL orders",
		}

	def _generate_condition_exit_orders(
		self,
		journal: Journal,
		day_data: Dict[str, Any],
		data_history: Dict[str, Any],
		exit_condition_formula: str
	) -> List[Dict[str, Any]]:
		"""Check open positions and generate SELL orders if condition is met.

		Args:
			journal: Journal for reading positions
			day_data: Pre-sliced market data {ticker: row} for the specific date
			data_history: Full price history for evaluating formulas
			exit_condition_formula: DSL formula to evaluate (e.g., sha_10_red[0] == 1)

		Returns:
			List of generated SELL orders
		"""
		exit_orders = []

		try:
			# Get all open positions from journal
			open_positions = journal.get_open_positions()
			self.logger.debug(f"Open positions for exit condition check: {len(open_positions)} positions")
			if open_positions.empty:
				self.logger.debug("No open positions to check")
				return exit_orders

			for _, position in open_positions.iterrows():
				ticker = str(position.get("ticker", ""))
				quantity = int(position.get("quantity", 0))

				self.logger.debug(f"  Position {ticker}: qty={quantity}")

				if quantity <= 0:
					self.logger.debug(f"    Skipping: zero qty")
					continue

				# Get market data for evaluation
				if ticker not in day_data:
					self.logger.debug(f"    No market data for {ticker}")
					continue

				market_row = day_data[ticker]

				# Evaluate exit condition formula
				try:
					# If we have full data_history for this ticker, use it (better for DSL with shifts)
					if ticker in data_history:
						eval_data = data_history[ticker]
						self.logger.debug(f"    Using data_history for {ticker} ({len(eval_data)} rows)")
					else:
						# Fallback to single row
						eval_data = market_row
						self.logger.debug(f"    Using single market row for {ticker}")

					condition_met = evaluate(exit_condition_formula, eval_data)
					self.logger.debug(f"    Condition result: {condition_met}")

					if condition_met:
						self.logger.info(f"EXIT CONDITION MET: {ticker}")

						# Get exit price from market data (use close)
						exit_price = float(market_row.get("close", 0)) if "close" in market_row else None
						if exit_price is None or exit_price <= 0:
							self.logger.warning(f"  Invalid exit price for {ticker}, skipping")
							continue

						# Generate SELL order (don't execute directly)
						sell_order = {
							"ticker": ticker,
							"quantity": quantity,
							"execution_method": "market",
							"exit_type": "condition",
							"exit_price": exit_price,
							"metadata": {
								"formula": exit_condition_formula,
								"reason": "exit_condition_met"
							}
						}
						exit_orders.append(sell_order)

						self.logger.info(
							f"Generated SELL order: {quantity} {ticker} @ {exit_price:.2f} "
							f"(exit condition: {exit_condition_formula})"
						)
					else:
						self.logger.debug(f"    Condition not met")

				except Exception as e:
					self.logger.debug(f"Error evaluating condition for {ticker}: {e}")
					continue

		except Exception as e:
			self.logger.error(f"Error generating condition exit orders: {e}")

		return exit_orders

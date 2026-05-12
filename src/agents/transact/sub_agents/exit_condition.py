"""Exit condition agent for handling formula-based exits."""

from typing import Any, Dict, Optional, List
from datetime import date as date_type
from core.agent import Agent
from tools.portfolio.journal import Journal
from tools.portfolio.orders import Orders
from tools.formula.calculator import evaluate


class ExitConditionAgent(Agent):
	"""Execute exits based on condition formula evaluation.

	Checks all open positions against exit condition formula and exits
	any that match the condition (formula evaluates to True).
	"""

	def __init__(self, name: str = "ExitConditionAgent"):
		"""Initialize exit condition agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute condition-based exits for open positions.

		Args:
			input_data: Input data with:
				- portfolio_name: Portfolio to execute exits for
				- trading_date: Date of execution
				- day_data: Pre-sliced market data {ticker: row}
				- data_history: Full price history {ticker: DataFrame}

		Returns:
			Response with exit execution results
		"""
		if input_data is None:
			input_data = {}

		portfolio_name = self.context.get("portfolio_name") or "default"
		trading_date = self.context.get("date")
		day_data = input_data.get("day_data") or self.context.get("day_data") or {}
		data_history = input_data.get("data_history") or self.context.get("data_history") or {}

		if not trading_date:
			return {
				"status": "error",
				"message": "date not set in context",
				"output": {"executed": 0, "exits": []},
			}

		# Get exit condition formula from strategy config
		strategy_config = self.context.get("strategy_config") or {}
		exit_config = strategy_config.get("exit", {}).get("parameters", {})
		exit_condition_formula = exit_config.get("condition", {}).get("formula")

		self.logger.debug(f"Exit condition formula from config: {repr(exit_condition_formula)}")

		if not exit_condition_formula or exit_condition_formula.lower() == "false":
			return {
				"status": "success",
				"output": {"executed": 0, "exits": []},
				"message": "No exit condition formula configured",
			}

		journal = Journal(portfolio_name, context=self.context.__dict__)
		exit_results = self._execute_condition_exits(
			journal, portfolio_name, trading_date, day_data, data_history, exit_condition_formula
		)

		return {
			"status": "success",
			"output": {
				"executed": len([r for r in exit_results if r.get("status") == "filled"]),
				"exits": exit_results,
			},
			"message": f"Executed {len([r for r in exit_results if r.get('status') == 'filled'])} condition-based exits",
		}

	def _execute_condition_exits(
		self,
		journal: Journal,
		portfolio_name: str,
		trading_date: date_type,
		day_data: Dict[str, Any],
		data_history: Dict[str, Any],
		exit_condition_formula: str
	) -> List[Dict[str, Any]]:
		"""Check open positions and execute exits if condition is met.

		Args:
			journal: Journal for reading positions and recording exits
			portfolio_name: Portfolio name
			trading_date: Date of execution
			day_data: Pre-sliced market data {ticker: row} for the specific date
			data_history: Full price history for evaluating formulas
			exit_condition_formula: DSL formula to evaluate (e.g., sha_10_red[0] == 1)

		Returns:
			List of exit execution results
		"""
		execution_results = []
		orders_mgr = Orders(portfolio_name, context=self.context.__dict__)

		try:
			# Get all open positions from journal
			open_positions = journal.get_open_positions()
			self.logger.debug(f"Open positions for exit condition check: {len(open_positions)} positions")
			if open_positions.empty:
				self.logger.debug("No open positions to check")
				return execution_results

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

						execution_result = {
							"ticker": ticker,
							"quantity": quantity,
							"status": "filled",
							"exit_price": exit_price,
							"exit_quantity": quantity,
							"reason": "exit_condition_met",
							"formula": exit_condition_formula,
						}
						execution_results.append(execution_result)

						# Get market data row for metadata (handles pandas Series or dict)
						market_metadata = {}
						if market_row is not None:
							try:
								if hasattr(market_row, 'items'):  # pandas Series or dict
									for key, value in market_row.items():
										try:
											market_metadata[key] = float(value) if value is not None else None
										except (ValueError, TypeError):
											market_metadata[key] = value
							except Exception:
								pass

						# Record SELL transaction in journal
						journal.add_transaction(
							operation="SELL",
							ticker=ticker,
							quantity=quantity,
							price=exit_price,
							fees=0,
							notes=f"Exit condition exit @ {exit_price:.2f}",
							created_at=f"{trading_date.isoformat()}T14:00:00.000000",
							exit_type="condition",
							status_at=f"{trading_date.isoformat()}T14:00:00.000000",
							metadata=market_metadata
						)

						# Mark related pending orders as executed
						self._mark_orders_executed(orders_mgr, ticker)

						self.logger.info(
							f"EXIT {quantity} {ticker} @ {exit_price:.2f} "
							f"(exit condition: {exit_condition_formula})"
						)
					else:
						self.logger.debug(f"    Condition not met")

				except Exception as e:
					self.logger.debug(f"Error evaluating condition for {ticker}: {e}")
					continue

		except Exception as e:
			self.logger.error(f"Error executing condition exits: {e}")

		return execution_results

	def _mark_orders_executed(self, orders_mgr: Orders, ticker: str) -> None:
		"""Mark all pending orders for a ticker as executed.

		Args:
			orders_mgr: Orders manager
			ticker: Ticker symbol to mark
		"""
		try:
			pending = orders_mgr.get_pending_orders()
			if pending.empty:
				return

			for _, order in pending.iterrows():
				if str(order.get("ticker", "")).upper() == ticker.upper():
					order_id = str(order.get("id", ""))
					orders_mgr.update_order_status(order_id, "executed")
					self.logger.debug(f"Marked order {order_id[:8]} as executed")
		except Exception as e:
			self.logger.debug(f"Could not mark orders as executed: {e}")

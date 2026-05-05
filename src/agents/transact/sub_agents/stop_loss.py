"""Stop loss exit agent for handling stop loss triggered exits."""

from typing import Any, Dict, Optional, List
from datetime import date as date_type
from core.agent import Agent
from tools.portfolio.journal import Journal
from tools.portfolio.orders import Orders


class StopLossAgent(Agent):
	"""Execute stop loss exits when price falls below stop loss level.

	Checks all open positions and exits any that hit their stop loss price.
	Uses journal as source of truth for positions (no broker dependency).
	"""

	def __init__(self, name: str = "StopLossAgent"):
		"""Initialize stop loss agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute stop loss exits for positions that hit their stop loss.

		Args:
			input_data: Input data with:
				- portfolio_name: Portfolio to execute exits for
				- trading_date: Date of execution
				- day_data: Pre-sliced market data {ticker: row}

		Returns:
			Response with exit execution results
		"""
		if input_data is None:
			input_data = {}

		portfolio_name = self.context.get("portfolio_name") or "default"
		trading_date = self.context.get("date")
		day_data = input_data.get("day_data") or self.context.get("day_data") or {}

		if not trading_date:
			return {
				"status": "error",
				"message": "date not set in context",
				"output": {"executed": 0, "exits": []},
			}

		journal = Journal(portfolio_name, context=self.context.__dict__)
		exit_results = self._execute_stop_loss_exits(journal, portfolio_name, trading_date, day_data)

		return {
			"status": "success",
			"output": {
				"executed": len([r for r in exit_results if r.get("status") == "filled"]),
				"exits": exit_results,
			},
			"message": f"Executed {len([r for r in exit_results if r.get('status') == 'filled'])} stop loss exits",
		}

	def _execute_stop_loss_exits(
		self,
		journal: Journal,
		portfolio_name: str,
		trading_date: date_type,
		day_data: Dict[str, Any]
	) -> List[Dict[str, Any]]:
		"""Check open positions and execute exits if stop_loss hit.

		Records SELL transactions directly in journal (no broker needed).
		Marks corresponding orders as executed.

		Args:
			journal: Journal for reading positions and recording exits
			portfolio_name: Portfolio name
			trading_date: Date of execution
			day_data: Pre-sliced market data {ticker: row} for the specific date

		Returns:
			List of exit execution results
		"""
		execution_results = []
		orders_mgr = Orders(portfolio_name, context=self.context.__dict__)

		try:
			# Get all open positions from journal (source of truth)
			open_positions = journal.get_open_positions()
			self.logger.debug(f"StopLossAgent: Checking {len(open_positions)} open positions")
			if open_positions.empty:
				return execution_results

			for _, position in open_positions.iterrows():
				ticker = str(position.get("ticker", ""))
				quantity = int(position.get("quantity", 0))
				stop_loss = float(position.get("stop_loss", 0)) if position.get("stop_loss") else None

				self.logger.debug(f"  Position {ticker}: qty={quantity}, SL={stop_loss}")

				if not stop_loss or quantity <= 0:
					self.logger.debug(f"    Skipping: no SL or zero qty")
					continue

				# Get market data for today (day_data is {ticker: row}, pre-sliced)
				day_low = self._get_day_low(ticker, day_data)
				self.logger.debug(f"    day_low={day_low}")
				if day_low is None:
					self.logger.debug(f"    No market data")
					continue

				# Check if stop_loss was hit
				if day_low <= stop_loss:
					self.logger.info(f"STOP LOSS HIT: {ticker} day_low={day_low:.2f} <= SL={stop_loss:.2f}")

					# Execute EXIT at stop_loss price
					exit_price = stop_loss

					execution_result = {
						"ticker": ticker,
						"quantity": quantity,
						"stop_loss": stop_loss,
						"day_low": day_low,
						"status": "filled",
						"exit_price": exit_price,
						"exit_quantity": quantity,
						"reason": "stop_loss_hit",
					}
					execution_results.append(execution_result)

					# Record SELL transaction in journal
					journal.add_transaction(
						operation="SELL",
						ticker=ticker,
						quantity=quantity,
						price=exit_price,
						fees=0,
						notes=f"Stop loss exit @ {exit_price:.2f}",
						created_at=f"{trading_date.isoformat()}T14:00:00.000000"
					)

					# Mark related pending orders as executed
					self._mark_orders_executed(orders_mgr, ticker)

					self.logger.info(
						f"EXIT {quantity} {ticker} @ {exit_price:.2f} "
						f"(stop_loss hit at {stop_loss})"
					)
				else:
					self.logger.debug(f"    SL not hit: {day_low:.2f} > {stop_loss:.2f}")

		except Exception as e:
			self.logger.error(f"Error executing stop loss exits: {e}")

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

	def _get_day_low(self, ticker: str, day_data: Dict[str, Any]) -> Optional[float]:
		"""Get daily low price for ticker from day data.

		Args:
			ticker: Ticker symbol
			day_data: Pre-sliced market data {ticker: row}

		Returns:
			Daily low price or None
		"""
		if ticker not in day_data:
			return None

		row = day_data[ticker]
		try:
			return float(row.get("low")) if "low" in row else None
		except (ValueError, AttributeError):
			return None

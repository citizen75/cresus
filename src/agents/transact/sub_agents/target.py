"""Target profit exit agent for handling take_profit exits."""

from typing import Any, Dict, Optional, List
from datetime import date as date_type
from core.agent import Agent
from tools.portfolio.journal import Journal
from tools.portfolio.orders import Orders


class TargetAgent(Agent):
	"""Execute take_profit exits when price reaches target level.

	Checks all open positions and exits any that hit their take_profit price.
	Uses journal as source of truth for positions.
	"""

	def __init__(self, name: str = "TargetAgent"):
		"""Initialize target agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute take_profit exits for positions that hit their target.

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
		exit_results = self._execute_target_exits(journal, portfolio_name, trading_date, day_data)

		return {
			"status": "success",
			"output": {
				"executed": len([r for r in exit_results if r.get("status") == "filled"]),
				"exits": exit_results,
			},
			"message": f"Executed {len([r for r in exit_results if r.get('status') == 'filled'])} take_profit exits",
		}

	def _execute_target_exits(
		self,
		journal: Journal,
		portfolio_name: str,
		trading_date: date_type,
		day_data: Dict[str, Any]
	) -> List[Dict[str, Any]]:
		"""Check open positions and execute exits if take_profit hit.

		Records SELL transactions directly in journal.
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
			self.logger.debug(f"TargetAgent: Checking {len(open_positions)} open positions")
			if open_positions.empty:
				return execution_results

			for _, position in open_positions.iterrows():
				ticker = str(position.get("ticker", ""))
				quantity = int(position.get("quantity", 0))
				take_profit = float(position.get("take_profit", 0)) if position.get("take_profit") else None

				self.logger.debug(f"  Position {ticker}: qty={quantity}, TP={take_profit}")

				if not take_profit or quantity <= 0:
					self.logger.debug(f"    Skipping: no TP or zero qty")
					continue

				# Get market data for today (day_data is {ticker: row}, pre-sliced)
				day_high = self._get_day_high(ticker, day_data)
				self.logger.debug(f"    day_high={day_high}")
				if day_high is None:
					self.logger.debug(f"    No market data")
					continue

				# Check if take_profit was hit
				if day_high >= take_profit:
					self.logger.info(f"TARGET HIT: {ticker} day_high={day_high:.2f} >= TP={take_profit:.2f}")

					# Execute EXIT at take_profit price
					exit_price = take_profit

					execution_result = {
						"ticker": ticker,
						"quantity": quantity,
						"take_profit": take_profit,
						"day_high": day_high,
						"status": "filled",
						"exit_price": exit_price,
						"exit_quantity": quantity,
						"reason": "take_profit_hit",
					}
					execution_results.append(execution_result)

					# Record SELL transaction in journal
					journal.add_transaction(
						operation="SELL",
						ticker=ticker,
						quantity=quantity,
						price=exit_price,
						fees=0,
						notes=f"Take profit exit @ {exit_price:.2f}",
						created_at=f"{trading_date.isoformat()}T14:00:00.000000"
					)

					# Mark related pending orders as executed
					self._mark_orders_executed(orders_mgr, ticker)

					self.logger.info(
						f"EXIT {quantity} {ticker} @ {exit_price:.2f} "
						f"(take_profit hit at {take_profit})"
					)
				else:
					self.logger.debug(f"    TP not hit: {day_high:.2f} < {take_profit:.2f}")

		except Exception as e:
			self.logger.error(f"Error executing take_profit exits: {e}")

		return execution_results

	def _get_day_high(self, ticker: str, day_data: Dict[str, Any]) -> Optional[float]:
		"""Get daily high price for ticker from day data.

		Args:
			ticker: Ticker symbol
			day_data: Pre-sliced market data {ticker: row}

		Returns:
			Daily high price or None
		"""
		if ticker not in day_data:
			return None

		row = day_data[ticker]
		try:
			return float(row.get("high")) if "high" in row else None
		except (ValueError, AttributeError):
			return None

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

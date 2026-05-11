"""Time limit exit agent for closing positions after holding period."""

from typing import Any, Dict, Optional, List
from datetime import date as date_type, timedelta
from core.agent import Agent
from tools.portfolio.journal import Journal
from tools.portfolio.orders import Orders


class TimeLimitAgent(Agent):
	"""Execute exits when holding period expires.

	Closes positions that have been held longer than the strategy's holding_period.
	Uses journal entry dates to track holding duration.
	"""

	def __init__(self, name: str = "TimeLimitAgent"):
		"""Initialize time limit agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute exits for positions exceeding holding period.

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

		# Get holding period from context (set by strategy config)
		holding_period = self.context.get("holding_period")
		if not holding_period:
			return {
				"status": "success",
				"output": {"executed": 0, "exits": []},
				"message": "No holding_period configured - time limit exits disabled",
			}

		journal = Journal(portfolio_name, context=self.context.__dict__)
		exit_results = self._execute_time_limit_exits(journal, portfolio_name, trading_date, day_data, holding_period)

		return {
			"status": "success",
			"output": {
				"executed": len([r for r in exit_results if r.get("status") == "filled"]),
				"exits": exit_results,
			},
			"message": f"Executed {len([r for r in exit_results if r.get('status') == 'filled'])} time limit exits",
		}

	def _execute_time_limit_exits(
		self,
		journal: Journal,
		portfolio_name: str,
		trading_date: date_type,
		day_data: Dict[str, Any],
		holding_period: int
	) -> List[Dict[str, Any]]:
		"""Check open positions and execute exits if holding period exceeded.

		Records SELL transactions directly in journal.
		Marks corresponding orders as executed.

		Args:
			journal: Journal for reading positions and recording exits
			portfolio_name: Portfolio name
			trading_date: Date of execution
			day_data: Pre-sliced market data {ticker: row} for the specific date
			holding_period: Maximum holding period in days

		Returns:
			List of exit execution results
		"""
		execution_results = []
		orders_mgr = Orders(portfolio_name, context=self.context.__dict__)

		try:
			# Get all open positions from journal
			open_positions = journal.get_open_positions()
			self.logger.debug(f"TimeLimitAgent: Checking {len(open_positions)} open positions (holding_period={holding_period} days)")
			if open_positions.empty:
				return execution_results

			# Get all buy transactions to find entry dates
			df = journal.load_df()
			if df.empty:
				return execution_results

			# Parse dates
			df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

			for _, position in open_positions.iterrows():
				ticker = str(position.get("ticker", ""))
				quantity = int(position.get("quantity", 0))

				if quantity <= 0:
					continue

				# Find earliest BUY transaction for this ticker
				ticker_buys = df[
					(df["ticker"].str.upper() == ticker.upper()) &
					(df["operation"].str.upper() == "BUY")
				]

				if ticker_buys.empty:
					continue

				entry_date = ticker_buys["created_at"].min()
				if pd.isna(entry_date):
					continue

				entry_date = entry_date.date()
				holding_days = (trading_date - entry_date).days

				self.logger.debug(f"  Position {ticker}: qty={quantity}, held {holding_days} days (limit={holding_period})")

				# Check if holding period exceeded
				if holding_days > holding_period:
					self.logger.info(f"TIME LIMIT: {ticker} held {holding_days} days > {holding_period} day limit")

					# Get exit price (close price for the day)
					exit_price = self._get_market_price(ticker, day_data)
					if exit_price is None:
						self.logger.debug(f"    No market data for {ticker}, skipping")
						continue

					execution_result = {
						"ticker": ticker,
						"quantity": quantity,
						"holding_days": holding_days,
						"holding_period": holding_period,
						"status": "filled",
						"exit_price": exit_price,
						"exit_quantity": quantity,
						"reason": "holding_period_exceeded",
					}
					execution_results.append(execution_result)

					# Record SELL transaction
					journal.add_transaction(
						operation="SELL",
						ticker=ticker,
						quantity=quantity,
						price=exit_price,
						fees=0,
						notes=f"Time limit exit after {holding_days} days",
						created_at=f"{trading_date.isoformat()}T14:00:00.000000",
						exit_type="expired",
						status_at=f"{trading_date.isoformat()}T14:00:00.000000"
					)

					# Mark related pending orders as executed
					self._mark_orders_executed(orders_mgr, ticker)

					self.logger.info(
						f"EXIT {quantity} {ticker} @ {exit_price:.2f} "
						f"(held {holding_days} days)"
					)

		except Exception as e:
			self.logger.error(f"Error executing time limit exits: {e}")

		return execution_results

	def _get_market_price(self, ticker: str, day_data: Dict[str, Any]) -> Optional[float]:
		"""Get closing price for ticker from day data.

		Args:
			ticker: Ticker symbol
			day_data: Pre-sliced market data {ticker: row}

		Returns:
			Closing price or None
		"""
		if ticker not in day_data:
			return None

		row = day_data[ticker]
		try:
			return float(row.get("close")) if "close" in row else None
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


# Import pandas for date operations
import pandas as pd

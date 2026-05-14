"""Time limit sub-agent for generating SELL orders after holding period."""

from typing import Any, Dict, Optional, List
from datetime import date as date_type
from core.agent import Agent
from tools.portfolio.journal import Journal
import pandas as pd


class TimeLimitAgent(Agent):
	"""Generate SELL orders for positions exceeding holding period.

	Checks all open positions and generates SELL orders for any that have been
	held longer than the configured holding_period. Does not execute directly -
	returns orders for TransactAgent to execute.
	"""

	def __init__(self, name: str = "TimeLimitAgent"):
		"""Initialize time limit agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Generate SELL orders for positions exceeding holding period.

		Args:
			input_data: Input data with:
				- day_data: Pre-sliced market data {ticker: row}

		Returns:
			Response with generated SELL orders
		"""
		if input_data is None:
			input_data = {}

		portfolio_name = self.context.get("portfolio_name") or "default"
		day_data = input_data.get("day_data") or self.context.get("day_data") or {}
		trading_date = self.context.get("date")

		# Get holding_period from context (set by strategy config)
		holding_period = self.context.get("holding_period")
		if not holding_period:
			return {
				"status": "success",
				"output": {"exit_orders": []},
				"message": "No holding_period configured - time limit exits disabled",
			}

		journal = Journal(portfolio_name, context=self.context.__dict__)
		exit_orders = self._generate_time_limit_orders(
			journal, day_data, trading_date, holding_period
		)

		return {
			"status": "success",
			"output": {
				"exit_orders": exit_orders,
			},
			"message": f"Generated {len(exit_orders)} time limit SELL orders",
		}

	def _generate_time_limit_orders(
		self,
		journal: Journal,
		day_data: Dict[str, Any],
		trading_date: Optional[date_type],
		holding_period: int
	) -> List[Dict[str, Any]]:
		"""Check open positions and generate SELL orders if holding period exceeded.

		Args:
			journal: Journal for reading positions
			day_data: Pre-sliced market data {ticker: row} for the specific date
			trading_date: Current trading date
			holding_period: Maximum holding period in days

		Returns:
			List of generated SELL orders
		"""
		exit_orders = []

		try:
			if not trading_date:
				self.logger.warning("No trading_date in context, skipping time limit check")
				return exit_orders

			# Get all open positions from journal
			open_positions = journal.get_open_positions()
			self.logger.debug(f"Checking {len(open_positions)} open positions for time limit (holding_period={holding_period})")
			if open_positions.empty:
				return exit_orders

			# Get all transactions to find entry dates
			df = journal.load_df()
			if df.empty:
				return exit_orders

			# Parse dates
			df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

			for _, position in open_positions.iterrows():
				ticker = str(position.get("ticker", ""))
				quantity = int(position.get("quantity", 0))

				if quantity <= 0:
					continue

				# Find the entry date of the current open position
				# Get all BUY and SELL transactions for this ticker
				ticker_txns = df[df["ticker"].str.upper() == ticker.upper()].copy()
				ticker_txns = ticker_txns.sort_values("created_at")

				if ticker_txns.empty:
					continue

				# Find the most recent BUY that is part of the current open position
				# by finding the last BUY after the last SELL (or just the last BUY if no SELL)
				sells = ticker_txns[ticker_txns["operation"].str.upper() == "SELL"]
				last_sell_idx = -1
				if not sells.empty:
					last_sell_idx = ticker_txns[ticker_txns["operation"].str.upper() == "SELL"].index[-1]

				# Get the most recent BUY after the last SELL
				buys_after_sell = ticker_txns[(ticker_txns["operation"].str.upper() == "BUY")]
				if not buys_after_sell.empty:
					if last_sell_idx >= 0:
						buys_after_sell = buys_after_sell[buys_after_sell.index > last_sell_idx]

					if buys_after_sell.empty:
						continue

					entry_date = buys_after_sell["created_at"].iloc[-1]  # Most recent BUY
				else:
					continue

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

					exit_order = {
						"ticker": ticker,
						"quantity": quantity,
						"exit_price": exit_price,
						"exit_type": "expired",
						"metadata": {
							"reason": "holding_period_exceeded",
							"holding_days": holding_days,
							"holding_period": holding_period,
						}
					}
					exit_orders.append(exit_order)
					self.logger.info(
						f"TIME LIMIT SELL {quantity} {ticker} @ {exit_price:.2f} "
						f"(held {holding_days} days)"
					)

		except Exception as e:
			self.logger.error(f"Error generating time limit orders: {e}")

		return exit_orders

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

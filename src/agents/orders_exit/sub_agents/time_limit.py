"""Time limit agent — generate SELL orders for positions past their holding period."""

from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd

from core.agent import Agent
from tools.portfolio.journal import Journal


class TimeLimitAgent(Agent):
	"""Generate SELL orders for positions that have exceeded the configured holding period.

	Reads holding_period (days) from:
	    strategy_config.exit.parameters.time_limit.holding_period

	The entry date for each position is the date of the most recent BUY transaction
	that opened the current holding (i.e. the last BUY after the last SELL).
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		if input_data is None:
			input_data = {}

		holding_period = self._get_holding_period()
		if holding_period is None:
			return {
				"status": "success",
				"output": {"exit_orders": []},
				"message": "No holding_period configured — time limit exits disabled",
			}

		trading_date = self._get_trading_date()
		if trading_date is None:
			return {
				"status": "success",
				"output": {"exit_orders": []},
				"message": "No date in context — skipping time limit check",
			}

		portfolio_name = self.context.get("portfolio_name") or "default"
		day_data = self.context.get("day_data") or {}

		journal = Journal(portfolio_name, context=self.context.__dict__)
		exit_orders = self._generate_orders(journal, day_data, trading_date, holding_period)

		return {
			"status": "success",
			"output": {"exit_orders": exit_orders},
			"message": f"Generated {len(exit_orders)} time-limit SELL order(s)",
		}

	# ------------------------------------------------------------------
	# Private helpers
	# ------------------------------------------------------------------

	def _get_holding_period(self) -> Optional[int]:
		strategy_config = self.context.get("strategy_config") or {}
		hp = (
			strategy_config
			.get("exit", {})
			.get("parameters", {})
			.get("time_limit", {})
			.get("holding_period")
		)
		return int(hp) if hp is not None else None

	def _get_trading_date(self) -> Optional[date]:
		raw = self.context.get("date")
		if raw is None:
			return None
		if isinstance(raw, date):
			return raw
		try:
			return date.fromisoformat(str(raw))
		except (ValueError, TypeError):
			return None

	def _generate_orders(
		self,
		journal: Journal,
		day_data: Dict[str, Any],
		trading_date: date,
		holding_period: int,
	) -> List[Dict[str, Any]]:
		exit_orders: List[Dict[str, Any]] = []

		df = journal.load_df()
		if df.empty:
			return exit_orders

		open_positions = journal.get_open_positions()
		if open_positions.empty:
			return exit_orders

		df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

		for _, position in open_positions.iterrows():
			ticker = str(position.get("ticker", ""))
			quantity = position.get("quantity")
			if quantity is None or float(quantity) <= 0:
				continue

			entry_date = self._find_entry_date(df, ticker)
			if entry_date is None:
				continue

			holding_days = (trading_date - entry_date).days
			self.logger.debug(f"[TIME] {ticker}: held {holding_days}d / limit {holding_period}d")

			if holding_days <= holding_period:
				continue

			close_price = self._price(ticker, day_data, "close")
			if close_price is None:
				self.logger.debug(f"[TIME] {ticker}: no close price — skipping")
				continue

			self.logger.info(
				f"[TIME] {ticker}: {holding_days}d > {holding_period}d → SELL @ {close_price:.2f}"
			)
			exit_orders.append({
				"ticker": ticker,
				"quantity": float(quantity),
				"exit_price": close_price,
				"exit_type": "expired",
				"execution_method": "market",
				"metadata": {
					"reason": "holding_period_exceeded",
					"holding_days": holding_days,
					"holding_period": holding_period,
				},
			})

		return exit_orders

	@staticmethod
	def _find_entry_date(df: pd.DataFrame, ticker: str) -> Optional[date]:
		"""Return the date of the most recent BUY that opened the current position."""
		ticker_df = df[df["ticker"].str.upper() == ticker.upper()].sort_values("created_at")
		if ticker_df.empty:
			return None

		buys = ticker_df[ticker_df["operation"].str.upper() == "BUY"]
		sells = ticker_df[ticker_df["operation"].str.upper() == "SELL"]

		# Only consider BUYs that happened after the last SELL
		if not sells.empty:
			last_sell_time = sells["created_at"].iloc[-1]
			buys = buys[buys["created_at"] > last_sell_time]

		if buys.empty:
			return None

		entry_ts = buys["created_at"].iloc[-1]
		if pd.isna(entry_ts):
			return None
		return entry_ts.date()

	@staticmethod
	def _price(ticker: str, day_data: Dict[str, Any], field: str) -> Optional[float]:
		row = day_data.get(ticker)
		if row is None:
			return None
		try:
			v = row.get(field)
			return float(v) if v is not None else None
		except (ValueError, TypeError):
			return None

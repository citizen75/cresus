"""Trailing stop agent for dynamic stop loss adjustment."""

from typing import Any, Dict, Optional, List
from datetime import date as date_type
from core.agent import Agent
from tools.portfolio.journal import Journal


class TrailingStopAgent(Agent):
	"""Manage trailing stops by updating stop loss as price rises.

	Tracks highest price achieved for each position and maintains a stop loss
	at a trailing distance below that highest price. Adjusts stop loss upward
	as new highs are reached (never moves downward).
	"""

	def __init__(self, name: str = "TrailingStopAgent"):
		"""Initialize trailing stop agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Update trailing stops for open positions.

		Checks all open positions with trailing stops enabled and adjusts
		their stop loss levels based on today's highest price.

		Args:
			input_data: Input data with:
				- portfolio_name: Portfolio name
				- trading_date: Date of update
				- day_data: Market data {ticker: row}

		Returns:
			Response with trailing stop updates
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
				"output": {"updated": 0, "updates": []},
			}

		journal = Journal(portfolio_name, context=self.context.__dict__)
		updates = self._update_trailing_stops(journal, portfolio_name, trading_date, day_data)

		return {
			"status": "success",
			"output": {
				"updated": len([u for u in updates if u.get("stop_loss_adjusted")]),
				"updates": updates,
			},
			"message": f"Updated trailing stops for {len([u for u in updates if u.get('stop_loss_adjusted')])} positions",
		}

	def _update_trailing_stops(
		self,
		journal: Journal,
		portfolio_name: str,
		trading_date: date_type,
		day_data: Dict[str, Any]
	) -> List[Dict[str, Any]]:
		"""Update trailing stops for open positions.

		For each open position with trailing_stop enabled:
		1. Get the highest price achieved (from position metadata)
		2. Calculate new trailing stop level (highest_price - trailing_distance)
		3. If new level > current stop_loss, update stop_loss in journal
		4. Track highest_price achieved today

		Args:
			journal: Journal for reading and updating positions
			portfolio_name: Portfolio name
			trading_date: Date of update
			day_data: Market data {ticker: row}

		Returns:
			List of trailing stop updates
		"""
		updates = []

		try:
			open_positions = journal.get_open_positions()
			if open_positions.empty:
				return updates

			for _, position in open_positions.iterrows():
				ticker = str(position.get("ticker", ""))
				stop_loss = float(position.get("stop_loss", 0)) if position.get("stop_loss") else None
				trailing_stop_distance = position.get("trailing_stop_distance")

				# Skip if no trailing stop configured
				if trailing_stop_distance is None:
					continue

				trailing_stop_distance = float(trailing_stop_distance) if trailing_stop_distance else None
				if trailing_stop_distance is None:
					continue

				self.logger.debug(f"TrailingStop {ticker}: checking trailing stop")

				# Get highest price achieved so far
				highest_price = float(position.get("highest_price", 0)) if position.get("highest_price") else None
				if highest_price is None:
					# Initialize with entry price
					entry_price = float(position.get("entry_price", 0)) if position.get("entry_price") else None
					highest_price = entry_price

				# Get today's high price
				day_high = self._get_day_high(ticker, day_data)
				if day_high is None:
					self.logger.debug(f"  No market data for {ticker}")
					continue

				# Update highest_price if today's high is higher
				new_highest = max(highest_price or 0, day_high)

				# Calculate new trailing stop level (highest - distance)
				new_stop_loss = new_highest - trailing_stop_distance

				self.logger.debug(
					f"  {ticker}: highest={highest_price:.2f}, "
					f"today_high={day_high:.2f}, new_highest={new_highest:.2f}, "
					f"distance={trailing_stop_distance:.2f}, "
					f"current_SL={stop_loss:.2f}, new_TS={new_stop_loss:.2f}"
				)

				# Update stop loss if new level is higher (only move up, never down)
				stop_loss_adjusted = False
				if new_stop_loss > stop_loss:
					self.logger.info(
						f"TRAILING STOP UPDATE: {ticker} "
						f"SL {stop_loss:.2f} → {new_stop_loss:.2f} "
						f"(highest: {new_highest:.2f})"
					)

					# Update position's stop loss in journal
					journal.update_position_stop_loss(ticker, new_stop_loss)

					# Update highest_price if it changed
					if new_highest > (highest_price or 0):
						journal.update_position_highest_price(ticker, new_highest)

					stop_loss_adjusted = True

				updates.append({
					"ticker": ticker,
					"entry_price": float(position.get("entry_price", 0)) if position.get("entry_price") else None,
					"current_stop_loss": stop_loss,
					"new_stop_loss": new_stop_loss,
					"highest_price": new_highest,
					"today_high": day_high,
					"trailing_distance": trailing_stop_distance,
					"stop_loss_adjusted": stop_loss_adjusted,
				})

		except Exception as e:
			self.logger.error(f"Error updating trailing stops: {e}")

		return updates

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

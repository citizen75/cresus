"""Trailing stop agent — update highest price and stop loss levels in the journal."""

from typing import Any, Dict, List, Optional

from core.agent import Agent
from tools.portfolio.journal import Journal


class TrailingStopAgent(Agent):
	"""Update trailing stop levels for open positions.

	For each open position with trailing_stop_distance set:
	  1. Compare today's high against stored highest_price
	  2. Update highest_price in journal when a new peak is reached
	  3. Compute new trailing stop = highest_price - trailing_stop_distance
	  4. Update stop_loss in journal when the new level exceeds the current one

	Runs before StopLossAgent so effective stop computation reads fresh values.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		if input_data is None:
			input_data = {}

		if not self.context.get("date"):
			return {
				"status": "error",
				"output": {"updated": 0},
				"message": "date not set in context",
			}

		portfolio_name = self.context.get("portfolio_name") or "default"
		day_data = self.context.get("day_data") or {}

		journal = Journal(portfolio_name, context=self.context.__dict__)
		updates = self._update_trailing_stops(journal, day_data)
		adjusted = sum(1 for u in updates if u.get("stop_loss_adjusted"))

		return {
			"status": "success",
			"output": {"updated": adjusted, "updates": updates},
			"message": f"Trailing stop updated for {adjusted} position(s)",
		}

	def _update_trailing_stops(
		self, journal: Journal, day_data: Dict[str, Any]
	) -> List[Dict[str, Any]]:
		updates: List[Dict[str, Any]] = []

		open_positions = journal.get_open_positions()
		if open_positions.empty:
			return updates

		for _, position in open_positions.iterrows():
			ticker = str(position.get("ticker", ""))
			trailing_dist = position.get("trailing_stop_distance")
			if trailing_dist is None:
				continue
			trailing_dist = float(trailing_dist)

			stop_loss = position.get("stop_loss")
			stop_loss = float(stop_loss) if stop_loss is not None else None

			# Seed highest_price from entry_price when position was just opened
			highest_price = position.get("highest_price")
			if highest_price is None:
				entry_price = position.get("entry_price")
				highest_price = float(entry_price) if entry_price is not None else None
			else:
				highest_price = float(highest_price)

			day_high = self._price(ticker, day_data, "high")
			if day_high is None:
				self.logger.debug(f"[TRAILING] {ticker}: no day_high — skipping")
				continue

			# Always update highest_price when a new peak is reached
			new_highest = max(highest_price or 0.0, day_high)
			if new_highest > (highest_price or 0.0):
				journal.update_position_highest_price(ticker, new_highest)
				self.logger.debug(f"[TRAILING] {ticker}: highest_price → {new_highest:.2f}")
			highest_price = new_highest

			# Move stop up when the new trailing level exceeds the current one
			new_stop = highest_price - trailing_dist
			stop_loss_adjusted = False
			if stop_loss is None or new_stop > stop_loss:
				journal.update_position_stop_loss(ticker, new_stop)
				self.logger.info(
					f"[TRAILING] {ticker}: stop {stop_loss} → {new_stop:.2f}"
					f" (highest={highest_price:.2f})"
				)
				stop_loss_adjusted = True

			updates.append({
				"ticker": ticker,
				"highest_price": highest_price,
				"day_high": day_high,
				"trailing_distance": trailing_dist,
				"new_stop": new_stop,
				"stop_loss_adjusted": stop_loss_adjusted,
			})

		return updates

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

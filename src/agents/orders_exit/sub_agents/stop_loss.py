"""Stop loss agent — compute effective stop loss levels for open positions."""

from typing import Any, Dict, Optional

from core.agent import Agent
from tools.portfolio.journal import Journal


class StopLossAgent(Agent):
	"""Compute effective stop loss levels for all open positions.

	Reads stop type from context["strategy_config"]:
	  fix      — use the stored stop_loss value as-is
	  trailing — compute highest_price - trailing_stop_distance

	Writes context["effective_stop_losses"] = {ticker: price}.

	Runs after TrailingStopAgent so highest_price already reflects today's data.
	Does not write to the journal.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		if input_data is None:
			input_data = {}

		portfolio_name = self.context.get("portfolio_name") or "default"
		stop_type = self._get_stop_type()

		journal = Journal(portfolio_name, context=self.context.__dict__)
		open_positions = journal.get_open_positions()

		if open_positions.empty:
			self.context.set("effective_stop_losses", {})
			return {"status": "success", "output": {"count": 0}, "message": "No open positions"}

		effective_stops: Dict[str, float] = {}
		for _, position in open_positions.iterrows():
			ticker = str(position.get("ticker", ""))
			quantity = position.get("quantity")
			stop_loss = position.get("stop_loss")

			if quantity is None or float(quantity) <= 0:
				continue
			if stop_loss is None:
				continue

			effective = float(stop_loss)

			if stop_type == "trailing":
				trailing_dist = position.get("trailing_stop_distance")
				trailing_pct = position.get("trailing_stop_pct")
				highest_price = position.get("highest_price")
				if trailing_pct is not None and highest_price is not None:
					effective = float(highest_price) * (1 - float(trailing_pct))
					self.logger.debug(
						f"[STOP] {ticker}: trailing = {float(highest_price):.2f}"
						f" * (1 - {float(trailing_pct):.4f}) = {effective:.2f}"
					)
				elif trailing_dist is not None and highest_price is not None:
					effective = float(highest_price) - float(trailing_dist)
					self.logger.debug(
						f"[STOP] {ticker}: trailing = {float(highest_price):.2f}"
						f" - {float(trailing_dist):.2f} = {effective:.2f}"
					)

			effective_stops[ticker] = effective

		self.context.set("effective_stop_losses", effective_stops)
		self.logger.debug(f"[STOP] Effective stops computed for {len(effective_stops)} position(s)")

		return {
			"status": "success",
			"output": {"count": len(effective_stops)},
			"message": f"Computed effective stop losses for {len(effective_stops)} position(s)",
		}

	def _get_stop_type(self) -> str:
		strategy_config = self.context.get("strategy_config") or {}
		return (
			strategy_config
			.get("exit", {})
			.get("parameters", {})
			.get("stop", {})
			.get("type", "fix")
		)

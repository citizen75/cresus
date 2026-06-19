"""Exit agent for evaluating exit conditions."""

from typing import Any, Dict, List, Optional

from core.agent import Agent
from agents.orders_exit.sub_agents import ExitConditionAgent, TrailingStopAgent, StopLossAgent, TimeLimitAgent
from tools.portfolio.journal import Journal


class OrdersExitAgent(Agent):
	"""Evaluate exit conditions for open positions and expose results via context.

	Sub-agent pipeline (via _run_sub_agent, all non-fatal):
	  1. TrailingStopAgent  — update highest_price + trailing stop in journal
	  2. StopLossAgent      — compute effective stops → context["effective_stop_losses"]
	  3. TimeLimitAgent     — SELL orders for positions past their holding period
	  4. ExitConditionAgent — SELL orders for formula-based exits

	After collection, stop-loss precedence is applied: condition exits where the
	day's low breached the effective stop level are reclassified as stop_loss exits.

	Does NOT save orders — sets context["exit_orders"] for OrdersSendingAgent to persist.
	"""

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		if input_data is None:
			input_data = {}

		portfolio_name = self.context.get("portfolio_name") or "default"

		journal = Journal(portfolio_name, context=self.context.__dict__)
		open_positions = journal.get_open_positions()
		if open_positions.empty:
			self.logger.debug("[EXIT] No open positions — skipping")
			self.context.set("exit_orders", [])
			return {
				"status": "success",
				"output": {"exit_orders": 0},
				"message": "No open positions to evaluate",
			}

		self.logger.info(f"[EXIT] Evaluating {len(open_positions)} open position(s)")

		# 1. Update trailing stops in journal (highest_price + stop_loss)
		self._run_sub_agent(TrailingStopAgent("TrailingStopAgent"), fatal=False)
		# 2. Compute effective stop losses from updated journal data
		self._run_sub_agent(StopLossAgent("StopLossAgent"), fatal=False)
		# 3. Time-limit exits
		time_resp = self._run_sub_agent(TimeLimitAgent("TimeLimitAgent"), fatal=False)
		# 4. Condition-based exits
		cond_resp = self._run_sub_agent(ExitConditionAgent("ExitConditionAgent"), fatal=False)

		# Merge results from both generating agents
		all_exit_orders: List[Dict[str, Any]] = []
		all_exit_orders.extend(time_resp.get("output", {}).get("exit_orders", []))
		all_exit_orders.extend(cond_resp.get("output", {}).get("exit_orders", []))

		# Reclassify condition exits that breached the stop level
		day_data = self.context.get("day_data") or {}
		all_exit_orders = self._apply_stop_loss_precedence(all_exit_orders, day_data)

		self.context.set("exit_orders", all_exit_orders)

		self.logger.info(f"[EXIT] Done — {len(all_exit_orders)} exit order(s) ready for sending")
		return {
			"status": "success",
			"output": {"exit_orders": len(all_exit_orders)},
			"message": f"Exit evaluation complete: {len(all_exit_orders)} order(s) pending",
		}

	# ------------------------------------------------------------------
	# Private helpers
	# ------------------------------------------------------------------

	def _apply_stop_loss_precedence(
		self, orders: List[Dict[str, Any]], day_data: Dict[str, Any]
	) -> List[Dict[str, Any]]:
		"""Reclassify condition exits as stop_loss when day_low ≤ effective stop."""
		effective_stops = self.context.get("effective_stop_losses") or {}
		if not effective_stops or not day_data:
			return orders

		for order in orders:
			if order.get("exit_type") != "condition":
				continue
			ticker = order.get("ticker")
			stop_price = effective_stops.get(ticker)
			if stop_price is None:
				continue
			try:
				row = day_data.get(ticker) or {}
				day_low = float(row.get("low")) if row.get("low") is not None else None
			except (ValueError, TypeError):
				day_low = None
			if day_low is None or day_low > stop_price:
				continue
			self.logger.info(
				f"[EXIT] Stop-loss precedence: {ticker} "
				f"condition_price={order.get('exit_price', 0):.2f} → stop={stop_price:.2f}"
			)
			order["exit_type"] = "stop_loss"
			order["exit_price"] = stop_price

		return orders


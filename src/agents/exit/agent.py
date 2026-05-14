"""Exit agent for evaluating exit conditions."""

from typing import Any, Dict, Optional, List
import json
from core.agent import Agent
from core.flow import Flow
from agents.exit.sub_agents import ExitConditionAgent, TrailingStopAgent, StopLossAgent, TimeLimitAgent
from tools.portfolio.journal import Journal
from tools.portfolio.orders import Orders


class ExitAgent(Agent):
	"""Agent for evaluating exit conditions and updating context.

	Evaluates exit conditions for all open positions and stores results
	in context for TransactAgent to execute. Does not create orders or transactions.

	Exit conditions evaluated:
	1. Stop loss (fix or trailing) - calculates effective levels
	2. Take profit targets
	3. Holding period limits
	4. Condition-based exits
	"""

	def __init__(self, name: str = "ExitAgent", context: Optional[Any] = None):
		"""Initialize exit agent.

		Args:
			name: Agent name
			context: AgentContext for shared state
		"""
		super().__init__(name, context)
		self.stop_loss_agent = StopLossAgent("StopLossAgent")
		self.trailing_stop_agent = TrailingStopAgent("TrailingStopAgent")
		self.exit_condition_agent = ExitConditionAgent("ExitConditionAgent")

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Evaluate exit conditions and save SELL orders.

		Evaluates all exit conditions for open positions and saves generated
		SELL orders to the Orders table for TransactAgent to execute.

		Args:
			input_data: Input data (optional, uses context)

		Returns:
			Response dictionary with saved order count
		"""
		if input_data is None:
			input_data = {}

		portfolio_name = self.context.get("portfolio_name") or "default"

		# Get data from context
		day_data = self.context.get("day_data") or {}
		data_history = self.context.get("data_history") or {}

		# Validate we have positions to check
		journal = Journal(portfolio_name, context=self.context.__dict__)
		open_positions = journal.get_open_positions()

		if open_positions.empty:
			self.logger.debug("No open positions to evaluate for exits")
			return {
				"status": "success",
				"output": {},
				"message": "No open positions to evaluate",
			}

		self.logger.info(f"[EXIT] Evaluating {len(open_positions)} open positions for exit conditions")

		# Create exit evaluation flow
		exit_flow = Flow("ExitEvaluationFlow", context=self.context)

		# Add stop loss evaluation (calculates effective stop losses)
		exit_flow.add_step(
			StopLossAgent("StopLossStep"),
			required=False
		)

		# Add trailing stop updates (updates highest price tracking)
		exit_flow.add_step(
			TrailingStopAgent("TrailingStopStep"),
			required=False
		)

		# Add time limit evaluation (generates SELL orders for exceeded holding periods)
		exit_flow.add_step(
			TimeLimitAgent("TimeLimitStep"),
			step_name="time_limit",
			required=False
		)

		# Add condition-based exit evaluation
		exit_flow.add_step(
			ExitConditionAgent("ExitConditionStep"),
			step_name="exit_condition",
			required=False
		)

		# Execute the flow (results stored in context, not orders)
		flow_result = exit_flow.process({
			"day_data": day_data,
			"data_history": data_history,
		})

		if flow_result.get("status") != "success":
			self.logger.warning(f"Exit evaluation flow failed: {flow_result.get('message', 'Unknown error')}")

		# Save SELL orders from exit agents (TimeLimitAgent and ExitConditionAgent)
		orders_saved = 0
		try:
			orders_mgr = Orders(portfolio_name, context=self.context.__dict__)
			trading_date = self.context.get("date")
			all_exit_orders = []

			# Extract TimeLimitAgent results
			for step in exit_flow.steps:
				if step.get("name") == "time_limit":
					time_limit_result = step.get("result", {})
					if time_limit_result and time_limit_result.get("status") == "success":
						time_limit_orders = time_limit_result.get("output", {}).get("exit_orders", [])
						all_exit_orders.extend(time_limit_orders)
					break

			# Extract ExitConditionAgent results
			for step in exit_flow.steps:
				if step.get("name") == "exit_condition":
					exit_condition_result = step.get("result", {})
					if exit_condition_result and exit_condition_result.get("status") == "success":
						condition_orders = exit_condition_result.get("output", {}).get("exit_orders", [])
						all_exit_orders.extend(condition_orders)
					break

			# Save all collected exit orders
			if all_exit_orders:
				for exit_order in all_exit_orders:
					ticker = exit_order.get("ticker")
					quantity = exit_order.get("quantity")
					exit_price = exit_order.get("exit_price")
					exit_type = exit_order.get("exit_type", "condition")

					# Create metadata for SELL order
					metadata = {
						"exit_type": exit_type,
						"formula": exit_order.get("metadata", {}).get("formula", ""),
						"reason": exit_order.get("metadata", {}).get("reason", "exit_condition_met")
					}

					# Format created_at timestamp
					created_at = None
					if trading_date:
						from datetime import datetime
						if isinstance(trading_date, str):
							created_at = f"{trading_date}T14:00:00.000000"
						else:
							created_at = f"{trading_date.isoformat()}T14:00:00.000000"

					orders_mgr.add_order(
						ticker=ticker,
						quantity=int(quantity),
						entry_price=float(exit_price),
						execution_method="market",
						operation="SELL",
						metadata=metadata,
						created_at=created_at,
						replace_same_day=False
					)
					orders_saved += 1
					self.logger.info(f"Saved SELL order: {quantity} {ticker} @ {exit_price:.2f} ({exit_type})")

				orders_mgr.flush()
		except Exception as e:
			self.logger.error(f"Error saving exit orders: {e}")

		self.logger.info(f"[EXIT] Exit evaluation complete - saved {orders_saved} SELL orders")

		return {
			"status": "success",
			"output": {"orders_saved": orders_saved},
			"message": f"Exit conditions evaluated and {orders_saved} SELL orders saved",
		}

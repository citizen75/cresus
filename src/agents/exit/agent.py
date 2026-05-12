"""Exit agent for evaluating and generating exit orders."""

from typing import Any, Dict, Optional, List
from core.agent import Agent
from core.flow import Flow
from agents.exit.sub_agents import ExitConditionAgent, TrailingStopAgent, StopLossAgent
from tools.portfolio.journal import Journal
from tools.portfolio.orders import Orders


class ExitAgent(Agent):
	"""Agent for evaluating exit conditions and generating SELL orders.

	Orchestrates exit analysis for open positions and generates SELL orders
	when exit conditions are met. Orders are passed to TransactAgent for execution.

	Exit conditions checked:
	1. Condition-based exits (formula evaluation)
	2. Stop loss (price-based exits at TransactAgent level)
	3. Take profit (price-based exits at TransactAgent level)
	4. Holding period (time-based exits at TransactAgent level)
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
		"""Generate SELL orders for open positions that meet exit conditions.

		Evaluates all exit conditions and generates SELL orders for positions
		that should be closed. Orders are saved to pending orders table.

		Args:
			input_data: Input data (optional, uses context)

		Returns:
			Response dictionary with generated SELL orders
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
				"output": {"exit_orders": []},
				"message": "No open positions to evaluate",
			}

		self.logger.info(f"[EXIT] Evaluating {len(open_positions)} open positions for exit conditions")

		# Create exit evaluation flow
		exit_flow = Flow("ExitEvaluationFlow", context=self.context)

		# Add stop loss exits (handles both fix and trailing types)
		exit_flow.add_step(
			StopLossAgent("StopLossStep"),
			required=False
		)

		# Add trailing stop update step (runs before condition evaluation)
		exit_flow.add_step(
			TrailingStopAgent("TrailingStopStep"),
			required=False
		)

		# Add condition-based exit evaluation
		exit_flow.add_step(
			ExitConditionAgent("ExitConditionStep"),
			required=False
		)

		# Execute the flow
		flow_result = exit_flow.process({
			"day_data": day_data,
			"data_history": data_history,
		})

		# Collect all exit orders from sub-agents
		all_exit_orders = []

		if flow_result.get("status") == "success":
			output = flow_result.get("output", {})
			all_exit_orders.extend(output.get("exit_orders", []))

		# Save exit orders to pending orders table
		orders_mgr = Orders(portfolio_name, context=self.context.__dict__)
		saved_order_ids = []

		for order in all_exit_orders:
			try:
				# Use add_order method with metadata flag to mark as SELL order
				metadata = {
					"order_type": "SELL",
					"exit_type": order.get("exit_type"),
					**order.get("metadata", {})
				}

				# Add market data to metadata if available
				day_data = self.context.get("day_data") or {}
				if day_data and order.get("ticker") in day_data:
					market_row = day_data[order.get("ticker")]
					if market_row is not None:
						try:
							if hasattr(market_row, 'items'):  # pandas Series or dict
								for key, value in market_row.items():
									if key not in metadata:  # Don't override order metadata
										try:
											metadata[key] = float(value) if value is not None else None
										except (ValueError, TypeError):
											metadata[key] = value
						except Exception:
							pass

				order_id = orders_mgr.add_order(
					ticker=order.get("ticker"),
					quantity=order.get("quantity"),
					entry_price=order.get("exit_price", 0),
					execution_method=order.get("execution_method", "market"),
					metadata=metadata,
					replace_same_day=False
				)
				saved_order_ids.append(order_id)
				self.logger.debug(f"Saved SELL order {order_id[:8]} for {order.get('ticker')}")
			except Exception as e:
				self.logger.error(f"Error saving SELL order for {order.get('ticker')}: {e}")

		self.logger.info(f"[EXIT] Generated {len(all_exit_orders)} SELL orders for {len(saved_order_ids)} saved")

		return {
			"status": "success",
			"output": {
				"exit_orders": all_exit_orders,
				"saved_order_ids": saved_order_ids,
			},
			"message": f"Generated and saved {len(all_exit_orders)} SELL orders",
		}

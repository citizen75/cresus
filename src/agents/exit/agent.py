"""Exit agent for evaluating exit conditions."""

from typing import Any, Dict, Optional, List
from core.agent import Agent
from core.flow import Flow
from agents.exit.sub_agents import ExitConditionAgent, TrailingStopAgent, StopLossAgent
from tools.portfolio.journal import Journal


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
		"""Evaluate exit conditions and update context.

		Evaluates all exit conditions for open positions and stores results
		in context. Does not create or save orders - TransactAgent handles execution.

		Args:
			input_data: Input data (optional, uses context)

		Returns:
			Response dictionary with evaluation status
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

		# Add condition-based exit evaluation
		exit_flow.add_step(
			ExitConditionAgent("ExitConditionStep"),
			required=False
		)

		# Execute the flow (results stored in context, not orders)
		flow_result = exit_flow.process({
			"day_data": day_data,
			"data_history": data_history,
		})

		if flow_result.get("status") != "success":
			self.logger.warning(f"Exit evaluation flow failed: {flow_result.get('message', 'Unknown error')}")

		self.logger.info(f"[EXIT] Exit evaluation complete")

		return {
			"status": "success",
			"output": {},
			"message": "Exit conditions evaluated, results in context",
		}

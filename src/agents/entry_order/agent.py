"""Entry order agent for converting entry signals to executable orders."""

from typing import Any, Dict, Optional
from core.agent import Agent
from core.flow import Flow
from agents.entry_order.sub_agents import (
	PositionSizingAgent,
	EntryTimingAgent,
	RiskGuardAgent,
	OrderConstructionAgent,
)


class EntryOrderAgent(Agent):
	"""Agent for converting entry opportunities to executable orders.

	Orchestrates four sub-agents to bridge entry analysis and order execution:
	1. Position Sizing - Calculate shares based on portfolio metrics
	2. Entry Timing - Determine execution method and timing
	3. Risk Guard - Validate portfolio-level constraints
	4. Order Construction - Assemble final executable orders

	Integrates with PortfolioManager to access portfolio state.
	"""

	def __init__(
		self,
		name: str = "EntryOrderAgent",
		context: Optional[Any] = None,
		sizing_method: str = "fractional",
		risk_percent: float = 2.0,
	):
		"""Initialize entry order agent.

		Args:
			name: Agent name
			context: AgentContext for shared state
			sizing_method: Position sizing method ("fractional", "kelly", "volatility")
			risk_percent: Risk percentage per trade (default 2%)
		"""
		super().__init__(name, context)
		self.sizing_method = sizing_method
		self.risk_percent = risk_percent

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process entry recommendations into executable orders.

		Executes four-step pipeline:
		1. Position Sizing - Calculate order sizes
		2. Entry Timing - Determine execution method
		3. Risk Guard - Validate constraints
		4. Order Construction - Build executable orders

		Args:
			input_data: Input data (optional, uses context)

		Returns:
			Response dictionary with executable orders
		"""
		if input_data is None:
			input_data = {}

		# Validate entry recommendations exist
		entry_recommendations = self.context.get("entry_recommendations")
		if not entry_recommendations:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": "No entry recommendations in context"
			}

		# Ensure portfolio_name is set
		portfolio_name = input_data.get("portfolio_name") or self.context.get("portfolio_name") or "default"
		self.context.set("portfolio_name", portfolio_name)

		# Ensure risk constraints are set
		risk_constraints = input_data.get("risk_constraints") or self.context.get("risk_constraints") or {}
		self.context.set("risk_constraints", risk_constraints)

		# Create order processing flow with sub-agents
		order_flow = Flow("EntryOrderFlow", context=self.context)

		# Add position sizing step
		order_flow.add_step(
			PositionSizingAgent(
				"PositionSizingStep",
				sizing_method=self.sizing_method,
				risk_percent=self.risk_percent,
			),
			required=True
		)

		# Add entry timing step
		order_flow.add_step(
			EntryTimingAgent("EntryTimingStep"),
			required=True
		)

		# Add risk guard step
		order_flow.add_step(
			RiskGuardAgent("RiskGuardStep"),
			required=True
		)

		# Add order construction step
		order_flow.add_step(
			OrderConstructionAgent("OrderConstructionStep"),
			required=True
		)

		# Execute the flow
		flow_result = order_flow.process(input_data)

		# Check flow execution
		if flow_result.get("status") != "success":
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Order processing flow failed: {flow_result.get('message', 'Unknown error')}"
			}

		# Get final executable orders from context
		executable_orders = self.context.get("executable_orders") or []

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"orders": executable_orders,
				"count": len(executable_orders),
				"recommendations_analyzed": len(entry_recommendations),
				"execution_methods": self._count_execution_methods(executable_orders),
				"total_order_value": sum(o["shares"] * o["entry_price"] for o in executable_orders),
				"total_risk": sum(o.get("risk_amount", 0) for o in executable_orders),
			},
			"execution_history": flow_result.get("execution_history", []),
		}

	def _count_execution_methods(self, orders: list) -> Dict[str, int]:
		"""Count orders by execution method.

		Args:
			orders: List of executable orders

		Returns:
			Dict with counts by method
		"""
		counts = {
			"market": 0,
			"limit": 0,
			"scale_in": 0,
		}

		for order in orders:
			method = order.get("execution_method", "market")
			if method in counts:
				counts[method] += 1

		return counts

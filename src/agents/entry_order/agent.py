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
from tools.portfolio import PortfolioManager
from tools.portfolio.broker import PaperBroker
from tools.portfolio.journal import Journal


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

		# Execute orders through broker if portfolio type is "paper"
		execution_results = []
		if executable_orders:
			pm = PortfolioManager()
			portfolio_config = self._get_portfolio_config(pm, portfolio_name)
			portfolio_type = portfolio_config.get("type", "paper") if portfolio_config else "paper"

			if portfolio_type == "paper":
				execution_results = self._execute_through_paper_broker(
					executable_orders,
					portfolio_name,
					pm
				)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"orders": executable_orders,
				"count": len(executable_orders),
				"executed": len([r for r in execution_results if r.get("status") == "filled"]),
				"recommendations_analyzed": len(entry_recommendations),
				"execution_methods": self._count_execution_methods(executable_orders),
				"total_order_value": sum(o["shares"] * o["entry_price"] for o in executable_orders),
				"total_risk": sum(o.get("risk_amount", 0) for o in executable_orders),
				"execution_results": execution_results if execution_results else None,
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

	def _get_portfolio_config(self, pm: PortfolioManager, portfolio_name: str) -> Optional[Dict[str, Any]]:
		"""Get portfolio configuration.

		Args:
			pm: PortfolioManager instance
			portfolio_name: Portfolio name

		Returns:
			Portfolio configuration dict
		"""
		try:
			import yaml
			from pathlib import Path
			import os

			config_path = pm.config_path
			if not config_path.exists():
				return None

			config = yaml.safe_load(config_path.read_text())
			for portfolio in config.get("portfolios", []):
				if portfolio.get("name") == portfolio_name:
					return portfolio

			return None
		except Exception as e:
			self.logger.error(f"Error loading portfolio config: {e}")
			return None

	def _execute_through_paper_broker(
		self,
		orders: list,
		portfolio_name: str,
		pm: PortfolioManager
	) -> list:
		"""Execute orders through PaperBroker and record in journal.

		Args:
			orders: List of executable orders
			portfolio_name: Portfolio name
			pm: PortfolioManager instance

		Returns:
			List of execution results
		"""
		execution_results = []
		broker = PaperBroker()
		journal = Journal(portfolio_name)

		try:
			for order in orders:
				# Convert order format for broker
				broker_order = {
					"ticker": order.get("ticker"),
					"quantity": order.get("shares"),
					"action": "BUY",
					"price": order.get("entry_price"),
					"stop_loss": order.get("stop_loss"),
					"target_price": order.get("take_profit"),
					"strategy_id": order.get("metadata", {}).get("strategy", "unknown"),
				}

				# Execute through broker
				result = broker.execute_order(broker_order)

				execution_results.append({
					"order_id": order.get("id"),
					"ticker": order.get("ticker"),
					"shares": order.get("shares"),
					"entry_price": order.get("entry_price"),
					"status": result.status,
					"filled_price": result.filled_price,
					"filled_quantity": result.filled_quantity,
					"reason": result.reason,
				})

				# Record in journal if filled
				if result.status == "filled":
					journal.add_transaction(
						operation="BUY",
						ticker=order.get("ticker"),
						quantity=result.filled_quantity,
						price=result.filled_price,
						fees=0,  # Paper trading has no fees
						notes=f"Strategy: {broker_order['strategy_id']} | Entry Score: {order.get('metadata', {}).get('entry_score', 0):.2f}"
					)

					self.logger.info(
						f"Executed {result.filled_quantity} {order.get('ticker')} @ ${result.filled_price:.2f}"
					)
				else:
					self.logger.warning(f"Order rejected: {result.reason}")

			# Update portfolio cache after execution
			pm.update_portfolio_cache(portfolio_name)

		except Exception as e:
			self.logger.error(f"Error executing orders through PaperBroker: {e}")

		return execution_results

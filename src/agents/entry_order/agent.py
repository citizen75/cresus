"""Entry order agent for converting entry signals to executable orders."""

from typing import Any, Dict, Optional
from core.agent import Agent
from core.flow import Flow
from agents.entry_order.sub_agents import (
	PositionDuplicateFilterAgent,
	PositionSizingAgent,
	EntryTimingAgent,
	RiskGuardAgent,
	OrderConstructionAgent,
)
from tools.portfolio import PortfolioManager
from tools.portfolio.broker import PaperBroker
from tools.portfolio.journal import Journal
from tools.portfolio.orders import Orders


class EntryOrderAgent(Agent):
	"""Agent for converting entry opportunities to executable orders.

	Orchestrates five sub-agents to bridge entry analysis and order execution:
	1. Position Duplicate Filter - Remove recommendations with existing positions
	2. Position Sizing - Calculate shares based on portfolio metrics
	3. Entry Timing - Determine execution method and timing
	4. Risk Guard - Validate portfolio-level constraints
	5. Order Construction - Assemble final executable orders

	Integrates with PortfolioManager to access portfolio state.
	"""

	def __init__(
		self,
		name: str = "EntryOrderAgent",
		context: Optional[Any] = None,
		sizing_method: str = "fractional",
		risk_percent: float = 2.0,
		execute: bool = False,
	):
		"""Initialize entry order agent.

		Args:
			name: Agent name
			context: AgentContext for shared state
			sizing_method: Position sizing method ("fractional", "kelly", "volatility")
			risk_percent: Risk percentage per trade (default 2%)
			execute: Whether to execute orders immediately (default False - pending only)
		"""
		super().__init__(name, context)
		self.sizing_method = sizing_method
		self.risk_percent = risk_percent
		self.execute = execute

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Process entry recommendations into executable orders.

		Executes five-step pipeline:
		1. Position Duplicate Filter - Remove duplicate position entries
		2. Position Sizing - Calculate order sizes
		3. Entry Timing - Determine execution method
		4. Risk Guard - Validate constraints
		5. Order Construction - Build executable orders

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

		# Add position duplicate filter step (before sizing)
		order_flow.add_step(
			PositionDuplicateFilterAgent("PositionDuplicateFilterStep"),
			required=True
		)

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

		# Apply max_daily_orders constraint if specified in strategy config
		strategy_config = self.context.get("strategy_config") or {}
		entry_config = strategy_config.get("entry", {})
		max_daily_orders_param = entry_config.get("parameters", {}).get("max_daily_orders")

		if max_daily_orders_param and executable_orders:
			try:
				# Extract numeric value from formula or use directly
				if isinstance(max_daily_orders_param, dict):
					max_daily = int(max_daily_orders_param.get("formula", 999))
				else:
					max_daily = int(max_daily_orders_param)

				if len(executable_orders) > max_daily:
					# Keep top N orders by score, discard the rest
					orders_with_scores = [
						(order, order.get("metadata", {}).get("entry_score", 0))
						for order in executable_orders
					]
					orders_with_scores.sort(key=lambda x: x[1], reverse=True)
					executable_orders = [order for order, score in orders_with_scores[:max_daily]]
					self.logger.info(
						f"Applied max_daily_orders limit: {max_daily}. "
						f"Reduced from {len(entry_recommendations)} recommendations to {len(executable_orders)} orders"
					)
			except (ValueError, TypeError) as e:
				self.logger.warning(f"Could not parse max_daily_orders constraint: {e}")

		# Execute orders through broker if execute=True and portfolio type is "paper"
		execution_results = []
		if executable_orders and self.execute:
			pm = PortfolioManager(context=self.context.__dict__)
			portfolio_config = self._get_portfolio_config(pm, portfolio_name)
			portfolio_type = portfolio_config.get("type", "paper") if portfolio_config else "paper"

			if portfolio_type == "paper":
				execution_results = self._execute_through_paper_broker(
					executable_orders,
					portfolio_name,
					pm
				)
		elif executable_orders and not self.execute:
			# Just save orders as pending without execution
			orders_mgr = Orders(portfolio_name, context=self.context.__dict__)
			for order in executable_orders:
				# Use trading date from context if available (backtesting), otherwise current time
				created_at = None
				context_date = self.context.get("date")
				if context_date:
					from datetime import datetime
					if isinstance(context_date, str):
						created_at = f"{context_date}T09:00:00.000000"  # 9 AM pre-market
					else:
						created_at = f"{context_date.isoformat()}T09:00:00.000000"

				metadata = order.get("metadata", {})
				orders_mgr.add_order(
					ticker=order.get("ticker"),
					quantity=order.get("shares"),
					entry_price=order.get("entry_price"),
					stop_loss=order.get("stop_loss"),
					take_profit=order.get("take_profit"),
					limit_price=order.get("limit_price"),
					trailing_stop_distance=order.get("trailing_stop_distance"),
					execution_method=order.get("execution_method", "market"),
					scale_count=order.get("scale_count", 1),
					risk_amount=order.get("risk_amount"),
					risk_reward=order.get("risk_reward"),
					metadata=metadata,
					created_at=created_at
				)
			self.logger.info(f"Created {len(executable_orders)} pending orders (not executed)")

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
		"""Execute orders through PaperBroker.

		Saves orders to Orders file first (pending status),
		then updates to executed after broker execution,
		and records filled trades in Journal transaction history.

		Args:
			orders: List of executable orders
			portfolio_name: Portfolio name
			pm: PortfolioManager instance

		Returns:
			List of execution results
		"""
		execution_results = []
		broker = PaperBroker()
		orders_mgr = Orders(portfolio_name, context=self.context.__dict__)
		journal = Journal(portfolio_name, context=self.context.__dict__)

		try:
			for order in orders:
				# Save order to Orders file (pending status)
				metadata = order.get("metadata", {})
				order_id = orders_mgr.add_order(
					ticker=order.get("ticker"),
					quantity=order.get("shares"),
					entry_price=order.get("entry_price"),
					stop_loss=order.get("stop_loss"),
					take_profit=order.get("take_profit"),
					execution_method=order.get("execution_method", "market"),
					scale_count=order.get("scale_count", 1),
					risk_amount=order.get("risk_amount"),
					risk_reward=order.get("risk_reward"),
					metadata=metadata
				)

				# Convert order format for broker
				broker_order = {
					"ticker": order.get("ticker"),
					"quantity": order.get("shares"),
					"action": "BUY",
					"price": order.get("entry_price"),
					"stop_loss": order.get("stop_loss"),
					"target_price": order.get("take_profit"),
					"strategy_id": metadata.get("strategy", "unknown"),
				}

				# Execute through broker
				result = broker.execute_order(broker_order)

				execution_results.append({
					"order_id": order_id,
					"ticker": order.get("ticker"),
					"shares": order.get("shares"),
					"entry_price": order.get("entry_price"),
					"status": result.status,
					"filled_price": result.filled_price,
					"filled_quantity": result.filled_quantity,
					"reason": result.reason,
				})

				# Update order status based on execution
				if result.status == "filled":
					# Update order status to executed
					orders_mgr.update_order_status(order_id, "executed")

					# Record transaction in journal (what actually happened)
					# Use trading date from context if available (backtesting), otherwise current time
					created_at = None
					context_date = self.context.get("date")
					if context_date:
						from datetime import datetime
						if isinstance(context_date, str):
							created_at = f"{context_date}T14:00:00.000000"  # Use 2 PM as market close
						else:
							created_at = f"{context_date.isoformat()}T14:00:00.000000"

					journal.add_transaction(
						operation="BUY",
						ticker=order.get("ticker"),
						quantity=result.filled_quantity,
						price=result.filled_price,
						fees=0,  # Paper trading has no fees
						stop_loss=order.get("stop_loss"),
						notes=f"Order {order_id}: {metadata.get('strategy', 'unknown')}",
						take_profit=order.get("take_profit"),
						trailing_stop_distance=order.get("trailing_stop_distance"),
						highest_price=result.filled_price,
						created_at=created_at
					)

					self.logger.info(
						f"Executed {result.filled_quantity} {order.get('ticker')} @ ${result.filled_price:.2f}"
					)
				else:
					# Update order status to rejected
					orders_mgr.update_order_status(order_id, "rejected")
					self.logger.warning(f"Order rejected: {result.reason}")

			# Update portfolio cache after execution
			pm.update_portfolio_cache(portfolio_name)

		except Exception as e:
			self.logger.error(f"Error executing orders through PaperBroker: {e}")

		return execution_results

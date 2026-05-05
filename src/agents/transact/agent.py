"""Transaction agent for executing pending orders on a specific date."""

from datetime import datetime, date as date_type
from typing import Any, Dict, Optional, List
from core.agent import Agent
from tools.portfolio import PortfolioManager
from tools.portfolio.orders import Orders
from tools.portfolio.journal import Journal
from tools.portfolio.broker import PaperBroker


class TransactAgent(Agent):
	"""Agent for executing pending orders on a specific trading date.

	Orchestrates order execution workflow:
	1. Load market data for the date using DataAgent
	2. Fetch pending orders for the portfolio
	3. Execute orders using PaperBroker
	4. Record executed trades in Journal
	5. Update portfolio cache

	Converts pending orders to executed and records transactions in journal.
	"""

	def __init__(self, name: str = "TransactAgent", context: Optional[Any] = None):
		"""Initialize transact agent.

		Args:
			name: Agent name
			context: AgentContext for shared state
		"""
		super().__init__(name, context)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute pending orders for a specific date.

		Assumes day data has already been loaded by TransactFlow into context.data_history.

		Args:
			input_data: Input data with:
				- date: Trading date (YYYY-MM-DD or date object)
				- portfolio_name: Portfolio to execute orders for

		Returns:
			Response with execution results
		"""
		if input_data is None:
			input_data = {}

		# Get parameters from context (set by TransactFlow)
		portfolio_name = self.context.get("portfolio_name") or "default"
		trading_date = self.context.get("date")

		if not trading_date:
			return {
				"status": "error",
				"input": input_data,
				"message": "date not set in context"
			}

		# Verify day data is available in context
		data_history = self.context.get("data_history")
		if not data_history:
			return {
				"status": "error",
				"input": input_data,
				"message": "Day data not loaded - ensure TransactFlow loads data before executing orders"
			}

		# Get pending orders
		orders_mgr = Orders(portfolio_name, context=self.context.__dict__)
		pending_orders = orders_mgr.get_pending_orders()

		if pending_orders.empty:
			return {
				"status": "success",
				"input": input_data,
				"output": {
					"executed": 0,
					"failed": 0,
					"details": [],
				},
				"message": f"No pending orders to execute on {trading_date}",
			}

		# Execute pending orders with pre-loaded data
		execution_results = self._execute_pending_orders(
			pending_orders,
			portfolio_name,
			trading_date
		)

		executed_count = len([r for r in execution_results if r.get("status") == "filled"])
		failed_count = len([r for r in execution_results if r.get("status") != "filled"])

		# Update portfolio cache
		pm = PortfolioManager(context=self.context.__dict__)
		pm.update_portfolio_cache(portfolio_name)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"portfolio": portfolio_name,
				"date": trading_date.isoformat(),
				"executed": executed_count,
				"failed": failed_count,
				"total": len(execution_results),
				"details": execution_results,
			},
			"message": f"Executed {executed_count}/{len(execution_results)} pending orders for {portfolio_name}",
		}

	def _execute_pending_orders(
		self,
		pending_orders,
		portfolio_name: str,
		trading_date: date_type
	) -> List[Dict[str, Any]]:
		"""Execute pending orders for a portfolio on a date.

		Args:
			pending_orders: DataFrame of pending orders
			portfolio_name: Portfolio name
			trading_date: Date of execution

		Returns:
			List of execution results
		"""
		execution_results = []
		broker = PaperBroker()
		orders_mgr = Orders(portfolio_name, context=self.context.__dict__)
		journal = Journal(portfolio_name, context=self.context.__dict__)

		try:
			for _, order_row in pending_orders.iterrows():
				order_id = str(order_row.get("id", ""))
				ticker = str(order_row.get("ticker", ""))
				quantity = int(order_row.get("quantity", 0))
				entry_price = float(order_row.get("entry_price", 0))

				# Convert order for broker
				broker_order = {
					"ticker": ticker,
					"quantity": quantity,
					"action": "BUY",
					"price": entry_price,
					"stop_loss": float(order_row.get("stop_loss")) if order_row.get("stop_loss") else None,
					"target_price": float(order_row.get("take_profit")) if order_row.get("take_profit") else None,
					"strategy_id": "transact",
				}

				# Execute through broker
				result = broker.execute_order(broker_order)

				execution_result = {
					"order_id": order_id,
					"ticker": ticker,
					"quantity": quantity,
					"entry_price": entry_price,
					"status": result.status,
					"filled_price": result.filled_price,
					"filled_quantity": result.filled_quantity,
					"reason": result.reason,
				}
				execution_results.append(execution_result)

				# Update order status and record transaction if filled
				if result.status == "filled":
					# Update order status to executed
					orders_mgr.update_order_status(order_id, "executed")

					# Record transaction in journal
					metadata = {}
					try:
						import json
						metadata_str = str(order_row.get("metadata", ""))
						if metadata_str:
							metadata = json.loads(metadata_str)
					except Exception:
						pass

					journal.add_transaction(
						operation="BUY",
						ticker=ticker,
						quantity=result.filled_quantity,
						price=result.filled_price,
						fees=0,  # Paper trading has no fees
						notes=f"Order {order_id} executed",
						created_at=f"{trading_date.isoformat()}T14:00:00.000000"  # 2 PM market close
					)

					self.logger.info(
						f"Executed {result.filled_quantity} {ticker} @ {result.filled_price:.2f} "
						f"(order {order_id[:8]})"
					)
				else:
					# Update order status to rejected
					orders_mgr.update_order_status(order_id, "rejected")
					self.logger.warning(f"Order {order_id[:8]} rejected: {result.reason}")

		except Exception as e:
			self.logger.error(f"Error executing pending orders: {e}")

		return execution_results

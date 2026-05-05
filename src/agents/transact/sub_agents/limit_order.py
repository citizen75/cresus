"""Limit order agent for handling limit-priced BUY and SELL orders."""

from typing import Any, Dict, Optional, List
from datetime import date as date_type
from core.agent import Agent
from tools.portfolio.orders import Orders
from tools.portfolio.journal import Journal
from tools.portfolio.broker import PaperBroker


class LimitOrderAgent(Agent):
	"""Execute limit orders at specified price limits.

	Handles pending BUY orders with limit prices and executes them
	only if market conditions meet the limit price criteria.
	"""

	def __init__(self, name: str = "LimitOrderAgent"):
		"""Initialize limit order agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute limit orders from pending order queue.

		Args:
			input_data: Input data with:
				- portfolio_name: Portfolio to execute orders for
				- trading_date: Date of execution
				- day_data: Pre-sliced market data {ticker: row}

		Returns:
			Response with order execution results
		"""
		if input_data is None:
			input_data = {}

		portfolio_name = self.context.get("portfolio_name") or "default"
		trading_date = self.context.get("date")
		day_data = input_data.get("day_data") or self.context.get("day_data") or {}

		if not trading_date:
			return {
				"status": "error",
				"message": "date not set in context",
				"output": {"executed": 0, "orders": []},
			}

		orders_mgr = Orders(portfolio_name, context=self.context.__dict__)
		journal = Journal(portfolio_name, context=self.context.__dict__)

		# Filter for limit orders only (orders with limit_offset or execution_method=limit)
		limit_orders = self._get_limit_orders(orders_mgr)
		if limit_orders.empty:
			return {
				"status": "success",
				"output": {"executed": 0, "orders": []},
				"message": "No limit orders to execute",
			}

		execution_results = self._execute_limit_orders(
			orders_mgr,
			journal,
			portfolio_name,
			trading_date,
			day_data,
			limit_orders
		)

		executed_count = len([r for r in execution_results if r.get("status") == "filled"])

		return {
			"status": "success",
			"output": {
				"executed": executed_count,
				"orders": execution_results,
			},
			"message": f"Executed {executed_count} limit orders",
		}

	def _get_limit_orders(self, orders_mgr: Orders) -> Any:
		"""Get pending limit orders from queue.

		Args:
			orders_mgr: Orders manager

		Returns:
			DataFrame of pending limit orders
		"""
		pending = orders_mgr.get_pending_orders()
		if pending.empty:
			return pending

		# Filter for limit orders (execution_method=limit or has limit_offset)
		# For now, return empty as this would be populated by order construction
		# In the future, could have orders with execution_method column
		return pending[pending.get("execution_method") == "limit"] if "execution_method" in pending.columns else pending.iloc[0:0]

	def _execute_limit_orders(
		self,
		orders_mgr: Orders,
		journal: Journal,
		portfolio_name: str,
		trading_date: date_type,
		day_data: Dict[str, Any],
		limit_orders: Any
	) -> List[Dict[str, Any]]:
		"""Execute pending limit orders using market data.

		Args:
			orders_mgr: Orders manager
			journal: Journal for recording transactions
			portfolio_name: Portfolio name
			trading_date: Date of execution
			day_data: Pre-sliced market data {ticker: row}
			limit_orders: DataFrame of limit orders

		Returns:
			List of execution results
		"""
		execution_results = []
		broker = PaperBroker()

		if limit_orders.empty:
			return execution_results

		try:
			for _, order_row in limit_orders.iterrows():
				order_id = str(order_row.get("id", ""))
				ticker = str(order_row.get("ticker", ""))
				quantity = int(order_row.get("quantity", 0))
				entry_price = float(order_row.get("entry_price", 0))
				limit_price = float(order_row.get("limit_price", entry_price))
				stop_loss = float(order_row.get("stop_loss", 0)) if order_row.get("stop_loss") else None
				take_profit = float(order_row.get("take_profit", 0)) if order_row.get("take_profit") else None

				# Get market price for the date (day_data is {ticker: row}, pre-sliced)
				market_price = self._get_market_price(ticker, day_data)
				if market_price is None:
					market_price = entry_price

				# For limit BUY orders, execute only if market price is at/below limit
				if market_price > limit_price:
					# Limit price not met, skip this order
					execution_result = {
						"order_id": order_id,
						"ticker": ticker,
						"quantity": quantity,
						"limit_price": limit_price,
						"market_price": market_price,
						"status": "pending",
						"reason": f"Market price {market_price:.2f} above limit {limit_price:.2f}",
					}
					execution_results.append(execution_result)
					continue

				# Execute at limit price
				execution_price = limit_price

				broker_order = {
					"ticker": ticker,
					"quantity": quantity,
					"action": "BUY",
					"price": execution_price,
					"stop_loss": stop_loss,
					"target_price": take_profit,
					"strategy_id": "transact_limit",
				}

				result = broker.execute_order(broker_order)

				execution_result = {
					"order_id": order_id,
					"ticker": ticker,
					"quantity": quantity,
					"limit_price": limit_price,
					"execution_price": execution_price,
					"status": result.status,
					"filled_price": result.filled_price,
					"filled_quantity": result.filled_quantity,
					"reason": result.reason,
				}
				execution_results.append(execution_result)

				# Update order status and record transaction if filled
				if result.status == "filled":
					orders_mgr.update_order_status(order_id, "executed")

					# Record BUY transaction in journal with stop loss and take profit
					journal.add_transaction(
						operation="BUY",
						ticker=ticker,
						quantity=result.filled_quantity,
						price=result.filled_price,
						fees=0,
						stop_loss=stop_loss,
						take_profit=take_profit,
						notes=f"Limit order {order_id[:8]} executed @ {limit_price:.2f}",
						created_at=f"{trading_date.isoformat()}T14:00:00.000000"
					)

					self.logger.info(
						f"LIMIT BUY {result.filled_quantity} {ticker} @ {result.filled_price:.2f} "
						f"(limit {limit_price:.2f}) [SL: {stop_loss}]"
					)
				else:
					orders_mgr.update_order_status(order_id, "pending")
					self.logger.warning(f"Limit order {order_id[:8]} not filled: {result.reason}")

		except Exception as e:
			self.logger.error(f"Error executing limit orders: {e}")

		return execution_results

	def _get_market_price(self, ticker: str, day_data: Dict[str, Any]) -> Optional[float]:
		"""Get closing price for ticker from day data.

		Args:
			ticker: Ticker symbol
			day_data: Pre-sliced market data {ticker: row}

		Returns:
			Closing price or None
		"""
		if ticker not in day_data:
			return None

		row = day_data[ticker]
		try:
			return float(row.get("close")) if "close" in row else None
		except (ValueError, AttributeError):
			return None

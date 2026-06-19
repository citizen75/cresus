"""Limit order agent for handling limit-priced BUY and SELL orders."""

from typing import Any, Dict, Optional, List
from datetime import date as date_type
from core.agent import Agent
from tools.portfolio.orders import Orders
from tools.portfolio.journal import Journal
from tools.portfolio.execution_helpers import broker_from_journal, get_price, row_to_metadata, trading_datetime


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
		self.logger.debug(f"[LimitOrderAgent] Found {len(limit_orders)} limit orders out of {len(orders_mgr.load_df())} total orders")
		if limit_orders.empty:
			self.logger.debug("[LimitOrderAgent] No limit orders to execute")
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

		# Filter for limit orders (execution_method=limit)
		if "execution_method" in pending.columns:
			return pending[pending["execution_method"] == "limit"]
		else:
			# No execution_method column, return empty
			return pending.iloc[0:0]

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
		broker = broker_from_journal(journal, logger=self.logger)

		if limit_orders.empty:
			return execution_results

		execution_time = trading_datetime(trading_date)

		for _, order_row in limit_orders.iterrows():
			try:
				order = orders_mgr.parse_order_row(order_row)
				order_id = order["id"]
				ticker = order["ticker"]
				quantity = order["quantity"]
				entry_price = order["entry_price"]

				# Use the pre-calculated limit_price from order creation
				# (formula was evaluated at order creation time with entry_price)
				# Fall back to entry_price if limit not set
				limit_price = order["limit_price"] if order["limit_price"] is not None else entry_price

				stop_loss = order["stop_loss"]
				take_profit = order["take_profit"]

				# Get market price for the date: use low price for limit BUY fill simulation
				# (best-case fill during the trading day), falling back to close
				market_price = self._get_fill_price(ticker, day_data)
				if market_price is None:
					market_price = entry_price

				self.logger.debug(f"[LimitOrder] {ticker}: market_price={market_price:.2f}, limit_price={limit_price:.2f}")

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

					market_metadata = row_to_metadata(day_data.get(ticker))

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
						created_at=execution_time,
						metadata=market_metadata
					)

					# NOTE: SL/TP management is handled by StopLossAgent and TargetAgent
					# which read the position from Journal and execute when price is hit.

					self.logger.info(
						f"LIMIT BUY {result.filled_quantity} {ticker} @ {result.filled_price:.2f} "
						f"(limit {limit_price:.2f}) [SL: {stop_loss}]"
					)
				else:
					orders_mgr.update_order_status(order_id, "pending")
					self.logger.warning(f"Limit order {order_id[:8]} not filled: {result.reason}")

			except Exception as e:
				self.logger.error(f"Error executing limit order {order_row.get('id', '')} for {order_row.get('ticker', '')}: {e}")

		return execution_results

	def _get_fill_price(self, ticker: str, day_data: Dict[str, Any]) -> Optional[float]:
		"""Get the best-case fill price for a limit BUY order from day data.

		Uses the day's low price to simulate whether a limit order would have
		filled, falling back to close if low is unavailable.

		Args:
			ticker: Ticker symbol
			day_data: Pre-sliced market data {ticker: row}

		Returns:
			Fill price, or None if no market data
		"""
		low_price = get_price(day_data, ticker, "low")
		if low_price is not None:
			return low_price
		return get_price(day_data, ticker, "close")

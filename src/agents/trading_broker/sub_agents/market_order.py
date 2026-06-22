"""Market order agent for handling market-priced BUY and SELL orders."""

from typing import Any, Dict, Optional, List
from datetime import date as date_type
import pandas as pd
from core.agent import Agent
from tools.portfolio.orders import Orders
from tools.portfolio.journal import Journal
from tools.portfolio.execution_helpers import broker_from_journal, get_price, row_to_metadata, trading_datetime


class MarketOrderAgent(Agent):
	"""Execute market orders at current market price.

	Handles pending BUY orders with market execution, executing them
	at the market price (close or open of current day).
	"""

	def __init__(self, name: str = "MarketOrderAgent"):
		"""Initialize market order agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute market orders from pending order queue.

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

		# Filter for market orders only (orders with execution_method=market)
		market_orders = self._get_market_orders(orders_mgr)
		self.logger.debug(f"[MarketOrderAgent] Found {len(market_orders)} market orders out of {len(orders_mgr.load_df())} total orders")
		self.logger.debug(f"[MarketOrderAgent] day_data has {len(day_data)} tickers: {list(day_data.keys())[:5] if day_data else 'empty'}")
		if market_orders.empty:
			self.logger.debug("[MarketOrderAgent] No market orders to execute")
			return {
				"status": "success",
				"output": {"executed": 0, "orders": []},
				"message": "No market orders to execute",
			}

		execution_results = self._execute_market_orders(
			orders_mgr,
			journal,
			portfolio_name,
			trading_date,
			day_data,
			market_orders
		)

		executed_count = len([r for r in execution_results if r.get("status") == "filled"])

		return {
			"status": "success",
			"output": {
				"executed": executed_count,
				"orders": execution_results,
			},
			"message": f"Executed {executed_count} market orders",
		}

	def _get_market_orders(self, orders_mgr: Orders) -> Any:
		"""Get pending market orders from queue.

		Excludes linked SL/TP orders (SELL orders with linked_order=true in metadata).
		These are executed separately only when price reaches the SL/TP level.

		NOTE: the non-linked SELL branch below is a defensive no-op in the current
		pipeline. TradingBroker._execute_sell_orders() runs before this agent and
		already claims every active SELL order (filled/rejected/left pending), so by
		the time this method runs there are no non-linked SELL orders still pending.
		Kept as a safety net in case the call order in TradingBroker.process() changes.

		Args:
			orders_mgr: Orders manager

		Returns:
			DataFrame of pending market orders (BUY orders and immediate SELL orders only)
		"""
		pending = orders_mgr.get_pending_orders()
		if pending.empty:
			return pending

		# Filter for market orders (execution_method=market or not set)
		if "execution_method" in pending.columns:
			market_orders = pending[pending["execution_method"].isin(["market", None])]
		else:
			# No execution_method column, return all pending orders
			market_orders = pending

		# Exclude SELL SL/TP orders (linked orders that execute only when price hits level)
		# These should be handled by StopLossAgent and TargetAgent, not MarketOrderAgent
		if "metadata" in market_orders.columns and "operation" in market_orders.columns:
			# Filter out SELL orders with linked_order=true in metadata
			filtered_orders = []
			for _, order in market_orders.iterrows():
				parsed = orders_mgr.parse_order_row(order)

				# BUY orders always pass through
				if parsed["operation"] == "BUY":
					filtered_orders.append(order)
					continue

				# For SELL orders, check if they're linked SL/TP orders
				# If linked_order=true, skip (handle in StopLossAgent/TargetAgent)
				# If linked_order=false or not set, include (exit condition SELL orders)
				if parsed["metadata"].get("linked_order"):
					continue

				# Include non-linked SELL orders (exit conditions)
				filtered_orders.append(order)

			if filtered_orders:
				return pd.DataFrame(filtered_orders)
			else:
				return pd.DataFrame()

		return market_orders

	def _execute_market_orders(
		self,
		orders_mgr: Orders,
		journal: Journal,
		portfolio_name: str,
		trading_date: date_type,
		day_data: Dict[str, Any],
		market_orders: Any
	) -> List[Dict[str, Any]]:
		"""Execute pending market orders using market data.

		Args:
			orders_mgr: Orders manager
			journal: Journal for recording transactions
			portfolio_name: Portfolio name
			trading_date: Date of execution
			day_data: Pre-sliced market data {ticker: row}
			market_orders: DataFrame of market orders

		Returns:
			List of execution results
		"""
		execution_results = []
		broker = broker_from_journal(journal, logger=self.logger)

		if market_orders.empty:
			return execution_results

		execution_time = trading_datetime(trading_date)

		for _, order_row in market_orders.iterrows():
			try:
				order = orders_mgr.parse_order_row(order_row)
				order_id = order["id"]
				ticker = order["ticker"]
				quantity = order["quantity"]
				operation = order["operation"]
				entry_price = order["entry_price"]
				stop_loss = order["stop_loss"]
				take_profit = order["take_profit"]
				trailing_stop_distance = order.get("trailing_stop_distance")
				trailing_stop_pct = order.get("trailing_stop_pct")

				# Get market price for the date (day_data is {ticker: row}, pre-sliced)
				market_price = get_price(day_data, ticker, "close")
				if market_price is None:
					market_price = entry_price

				# Execute at market price
				execution_price = market_price

				broker_order = {
					"ticker": ticker,
					"quantity": quantity,
					"action": operation,
					"price": execution_price,
					"stop_loss": stop_loss,
					"target_price": take_profit,
					"strategy_id": "transact_market",
				}

				result = broker.execute_order(broker_order)

				execution_result = {
					"order_id": order_id,
					"ticker": ticker,
					"quantity": quantity,
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

					# Record transaction in journal with stop loss and take profit (for BUY orders only)
					journal.add_transaction(
						operation=operation,
						ticker=ticker,
						quantity=result.filled_quantity,
						price=result.filled_price,
						fees=0,
						stop_loss=stop_loss,
						take_profit=take_profit,
						trailing_stop_distance=trailing_stop_distance,
						trailing_stop_pct=trailing_stop_pct,
						notes=f"Market order {order_id} executed",
						created_at=execution_time,
						metadata=market_metadata
					)

					# NOTE: SL/TP management is handled by StopLossAgent and TargetAgent
					# which read the position from Journal and execute when price is hit.
					# No separate orders needed in Orders table.

					self.logger.info(
						f"MARKET {operation} {result.filled_quantity} {ticker} @ {result.filled_price:.2f} "
						f"[SL: {stop_loss}]"
					)
				else:
					orders_mgr.update_order_status(order_id, "pending")
					self.logger.warning(f"Market order {order_id[:8]} not filled: {result.reason}")

			except Exception as e:
				self.logger.error(f"Error executing market order {order_row.get('id', '')} for {order_row.get('ticker', '')}: {e}")

		return execution_results

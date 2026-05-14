"""Market order agent for handling market-priced BUY and SELL orders."""

from typing import Any, Dict, Optional, List
from datetime import date as date_type
import pandas as pd
from core.agent import Agent
from tools.portfolio.orders import Orders
from tools.portfolio.journal import Journal
from tools.portfolio.broker import PaperBroker


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
			import json
			filtered_orders = []
			for _, order in market_orders.iterrows():
				operation = str(order.get("operation", "BUY")).upper()

				# BUY orders always pass through
				if operation == "BUY":
					filtered_orders.append(order)
					continue

				# For SELL orders, check if they're linked SL/TP orders
				# If linked_order=true, skip (handle in StopLossAgent/TargetAgent)
				# If linked_order=false or not set, include (exit condition SELL orders)
				try:
					metadata_str = order.get("metadata", "")
					if metadata_str:
						metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
						if metadata.get("linked_order"):
							# Skip linked SL/TP orders - they're handled separately
							continue
				except (json.JSONDecodeError, TypeError):
					pass

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
		broker = self._get_broker_with_positions(journal)

		if market_orders.empty:
			return execution_results

		try:
			for _, order_row in market_orders.iterrows():
				order_id = str(order_row.get("id", ""))
				ticker = str(order_row.get("ticker", ""))
				quantity = int(order_row.get("quantity", 0)) if order_row.get("quantity") else 0

				# Safe conversion to float with None handling
				entry_price_val = order_row.get("entry_price")
				entry_price = float(entry_price_val) if entry_price_val not in (None, "") else 0

				stop_loss_val = order_row.get("stop_loss")
				stop_loss = float(stop_loss_val) if stop_loss_val not in (None, "") else None

				take_profit_val = order_row.get("take_profit")
				take_profit = float(take_profit_val) if take_profit_val not in (None, "") else None

				# Get market price for the date (day_data is {ticker: row}, pre-sliced)
				market_price = self._get_market_price(ticker, day_data)
				if market_price is None:
					market_price = entry_price

				# Ensure market_price is a scalar, not a Series
				try:
					market_price = float(market_price)
				except (ValueError, TypeError):
					market_price = entry_price

				# Execute at market price
				execution_price = market_price

				broker_order = {
					"ticker": ticker,
					"quantity": quantity,
					"action": "BUY",
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

					# Get market data row for metadata (OHLCV + indicators at execution time)
					market_row = day_data.get(ticker)
					market_metadata = None

					if market_row is not None:
						# Extract OHLCV and indicators from row (pandas Series or dict)
						try:
							# Convert to dict if it's a Series
							if isinstance(market_row, pd.Series):
								market_metadata = market_row.to_dict()
							elif isinstance(market_row, dict):
								market_metadata = market_row.copy()
							else:
								market_metadata = dict(market_row)

							# Clean up: convert NaN to None, numeric values to floats, timestamps to strings
							for key in list(market_metadata.keys()):
								val = market_metadata[key]
								if pd.isna(val):
									market_metadata[key] = None
								elif isinstance(val, (int, float)):
									market_metadata[key] = float(val)
								elif hasattr(val, 'isoformat'):  # datetime/Timestamp
									market_metadata[key] = val.isoformat()
								elif isinstance(val, str):
									market_metadata[key] = val
								else:
									# Convert other types to string as fallback
									market_metadata[key] = str(val)
						except Exception as e:
							self.logger.debug(f"Error extracting market metadata for {ticker}: {e}")
							market_metadata = None

					# Record BUY transaction in journal with stop loss and take profit
					journal.add_transaction(
						operation="BUY",
						ticker=ticker,
						quantity=result.filled_quantity,
						price=result.filled_price,
						fees=0,
						stop_loss=stop_loss,
						take_profit=take_profit,
						notes=f"Market order {order_id[:8]} executed @ {execution_price:.2f}",
						created_at=f"{trading_date.isoformat()}T14:00:00.000000",
						metadata=market_metadata
					)

					# NOTE: SL/TP management is handled by StopLossAgent and TargetAgent
					# which read the position from Journal and execute when price is hit.
					# No separate orders needed in Orders table.

					self.logger.info(
						f"MARKET BUY {result.filled_quantity} {ticker} @ {result.filled_price:.2f} "
						f"[SL: {stop_loss}]"
					)
				else:
					orders_mgr.update_order_status(order_id, "pending")
					self.logger.warning(f"Market order {order_id[:8]} not filled: {result.reason}")

		except Exception as e:
			self.logger.error(f"Error executing market orders: {e}")

		return execution_results

	def _get_broker_with_positions(self, journal: Journal) -> Any:
		"""Create a broker initialized with current positions from journal.

		Args:
			journal: Journal with transaction history

		Returns:
			PaperBroker with positions loaded from journal
		"""
		broker = PaperBroker()

		# Load BUY transactions from journal to reconstruct positions
		journal_df = journal.load_df()
		if not journal_df.empty:
			buy_transactions = journal_df[journal_df["operation"].str.upper() == "BUY"]

			positions_dict = {}
			for ticker in buy_transactions["ticker"].unique():
				ticker_buys = buy_transactions[buy_transactions["ticker"] == ticker]
				total_quantity = 0
				weighted_price = 0

				for _, transaction in ticker_buys.iterrows():
					qty = float(transaction.get("quantity", 0))
					price = float(transaction.get("price", 0))
					total_quantity += qty
					weighted_price += qty * price

				if total_quantity > 0:
					positions_dict[ticker] = {
						"ticker": ticker,
						"quantity": int(total_quantity),
						"entry_price": weighted_price / total_quantity,
						"current_price": weighted_price / total_quantity,
						"stop_loss": None,
						"target_price": None,
						"strategy_id": "transact",
					}

			broker.positions = positions_dict

		return broker

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

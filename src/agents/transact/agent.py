"""Transaction agent for executing pending orders and managing exits on a specific date."""

from datetime import datetime, date as date_type
from typing import Any, Dict, Optional, List
import json
from core.agent import Agent
from tools.portfolio import PortfolioManager
from tools.portfolio.orders import Orders
from tools.portfolio.journal import Journal
from tools.portfolio.broker import PaperBroker


class TransactAgent(Agent):
	"""Agent for executing orders and managing exits on a specific trading date.

	Consolidates buy and exit execution:
	1. Execute pending BUY orders at market prices
	2. Check open positions against stop_loss
	3. Auto-exit positions that hit stop_loss
	4. Record all transactions (BUY and EXIT) in journal
	5. Update portfolio cache
	"""

	def __init__(self, name: str = "TransactAgent", context: Optional[Any] = None):
		"""Initialize transact agent.

		Args:
			name: Agent name
			context: AgentContext for shared state
		"""
		super().__init__(name, context)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Execute pending BUY orders and manage exits (stop_loss) for a specific date.

		Assumes day data has already been loaded by TransactFlow into context.data_history.

		Args:
			input_data: Input data with:
				- date: Trading date (YYYY-MM-DD or date object)
				- portfolio_name: Portfolio to execute orders for

		Returns:
			Response with execution results (BUY and EXIT)
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

		journal = Journal(portfolio_name, context=self.context.__dict__)
		orders_mgr = Orders(portfolio_name, context=self.context.__dict__)

		# Execute pending BUY orders
		buy_results = self._execute_buy_orders(
			orders_mgr,
			journal,
			portfolio_name,
			trading_date,
			data_history
		)

		# Check open positions and execute exits (stop_loss)
		exit_results = self._execute_stop_loss_exits(
			journal,
			portfolio_name,
			trading_date,
			data_history
		)

		buy_count = len([r for r in buy_results if r.get("status") == "filled"])
		exit_count = len([r for r in exit_results if r.get("status") == "filled"])
		total_executed = buy_count + exit_count

		# Update portfolio cache
		pm = PortfolioManager(context=self.context.__dict__)
		pm.update_portfolio_cache(portfolio_name)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"portfolio": portfolio_name,
				"date": trading_date.isoformat(),
				"buy_executed": buy_count,
				"exit_executed": exit_count,
				"total_executed": total_executed,
				"buy_details": buy_results,
				"exit_details": exit_results,
			},
			"message": f"Executed {buy_count} BUY + {exit_count} EXIT orders for {portfolio_name}",
		}

	def _execute_buy_orders(
		self,
		orders_mgr: Orders,
		journal: Journal,
		portfolio_name: str,
		trading_date: date_type,
		data_history: Dict[str, Any]
	) -> List[Dict[str, Any]]:
		"""Execute pending BUY orders using market data.

		Args:
			orders_mgr: Orders manager
			journal: Journal for recording transactions
			portfolio_name: Portfolio name
			trading_date: Date of execution
			data_history: Market data for the date

		Returns:
			List of buy execution results
		"""
		execution_results = []
		broker = PaperBroker()
		pending_orders = orders_mgr.get_pending_orders()

		if pending_orders.empty:
			return execution_results

		try:
			for _, order_row in pending_orders.iterrows():
				order_id = str(order_row.get("id", ""))
				ticker = str(order_row.get("ticker", ""))
				quantity = int(order_row.get("quantity", 0))
				entry_price = float(order_row.get("entry_price", 0))
				stop_loss = float(order_row.get("stop_loss", 0)) if order_row.get("stop_loss") else None
				take_profit = float(order_row.get("take_profit", 0)) if order_row.get("take_profit") else None

				# Get market price for the date
				market_price = self._get_market_price(ticker, data_history)
				if market_price is None:
					market_price = entry_price

				# Execute at better of entry_price or market price
				execution_price = min(market_price, entry_price)

				# Convert order for broker
				broker_order = {
					"ticker": ticker,
					"quantity": quantity,
					"action": "BUY",
					"price": execution_price,
					"stop_loss": stop_loss,
					"target_price": take_profit,
					"strategy_id": "transact",
				}

				# Execute through broker
				result = broker.execute_order(broker_order)

				execution_result = {
					"order_id": order_id,
					"ticker": ticker,
					"quantity": quantity,
					"entry_price": entry_price,
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

					# Record BUY transaction in journal
					journal.add_transaction(
						operation="BUY",
						ticker=ticker,
						quantity=result.filled_quantity,
						price=result.filled_price,
						fees=0,
						notes=f"Order {order_id[:8]} executed",
						created_at=f"{trading_date.isoformat()}T14:00:00.000000"
					)

					self.logger.info(
						f"BUY {result.filled_quantity} {ticker} @ {result.filled_price:.2f} "
						f"(order {order_id[:8]}) [SL: {stop_loss}]"
					)
				else:
					orders_mgr.update_order_status(order_id, "rejected")
					self.logger.warning(f"Order {order_id[:8]} rejected: {result.reason}")

		except Exception as e:
			self.logger.error(f"Error executing BUY orders: {e}")

		return execution_results

	def _execute_stop_loss_exits(
		self,
		journal: Journal,
		portfolio_name: str,
		trading_date: date_type,
		data_history: Dict[str, Any]
	) -> List[Dict[str, Any]]:
		"""Check open positions and execute exits if stop_loss hit.

		Args:
			journal: Journal for reading positions and recording exits
			portfolio_name: Portfolio name
			trading_date: Date of execution
			data_history: Market data for the date

		Returns:
			List of exit execution results
		"""
		execution_results = []
		broker = PaperBroker()

		try:
			# Get all open positions
			open_positions = journal.get_open_positions()
			if open_positions.empty:
				return execution_results

			for _, position in open_positions.iterrows():
				ticker = str(position.get("ticker", ""))
				quantity = int(position.get("quantity", 0))
				stop_loss = float(position.get("stop_loss", 0)) if position.get("stop_loss") else None

				if not stop_loss or quantity <= 0:
					continue

				# Get market data for today
				day_low = self._get_day_low(ticker, data_history)
				if day_low is None:
					continue

				# Check if stop_loss was hit
				if day_low <= stop_loss:
					# Execute EXIT at stop_loss price
					exit_price = stop_loss

					broker_order = {
						"ticker": ticker,
						"quantity": quantity,
						"action": "SELL",
						"price": exit_price,
						"strategy_id": "transact_stop_loss",
					}

					result = broker.execute_order(broker_order)

					execution_result = {
						"ticker": ticker,
						"quantity": quantity,
						"stop_loss": stop_loss,
						"day_low": day_low,
						"status": result.status,
						"exit_price": result.filled_price,
						"exit_quantity": result.filled_quantity,
						"reason": "stop_loss_hit",
					}
					execution_results.append(execution_result)

					# Record EXIT transaction in journal
					if result.status == "filled":
						journal.add_transaction(
							operation="SELL",
							ticker=ticker,
							quantity=result.filled_quantity,
							price=result.filled_price,
							fees=0,
							notes=f"Stop loss exit @ {stop_loss}",
							created_at=f"{trading_date.isoformat()}T14:00:00.000000"
						)

						self.logger.info(
							f"EXIT {result.filled_quantity} {ticker} @ {result.filled_price:.2f} "
							f"(stop_loss hit at {stop_loss})"
						)

		except Exception as e:
			self.logger.error(f"Error executing stop loss exits: {e}")

		return execution_results

	def _get_market_price(self, ticker: str, data_history: Dict[str, Any]) -> Optional[float]:
		"""Get closing price for ticker from day data.

		Args:
			ticker: Ticker symbol
			data_history: Market data dict

		Returns:
			Closing price or None
		"""
		if ticker not in data_history:
			return None

		df = data_history[ticker]
		if df.empty:
			return None

		# Get closing price from latest row
		latest = df.iloc[-1]
		return float(latest.get("close")) if "close" in latest else None

	def _get_day_low(self, ticker: str, data_history: Dict[str, Any]) -> Optional[float]:
		"""Get daily low price for ticker from day data.

		Args:
			ticker: Ticker symbol
			data_history: Market data dict

		Returns:
			Daily low price or None
		"""
		if ticker not in data_history:
			return None

		df = data_history[ticker]
		if df.empty:
			return None

		# Get low price from latest row
		latest = df.iloc[-1]
		return float(latest.get("low")) if "low" in latest else None

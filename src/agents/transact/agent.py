"""Transaction agent for executing pending orders and managing exits on a specific date."""

from datetime import datetime, date as date_type
from typing import Any, Dict, Optional, List
import json
from core.agent import Agent
from tools.portfolio import PortfolioManager
from tools.portfolio.orders import Orders
from tools.portfolio.journal import Journal
from tools.portfolio.broker import PaperBroker
from .sub_agents import StopLossAgent, TargetAgent, TimeLimitAgent, LimitOrderAgent, TrailingStopAgent


class TransactAgent(Agent):
	"""Agent for executing orders and managing exits on a specific trading date.

	Consolidates buy and exit execution using pluggable subagents:
	1. Execute pending BUY orders at market prices
	2. Check open positions against stop_loss via StopLossAgent
	3. Execute limit orders via LimitOrderAgent
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
		self.trailing_stop_agent = TrailingStopAgent("TrailingStopAgent")
		self.stop_loss_agent = StopLossAgent("StopLossAgent")
		self.target_agent = TargetAgent("TargetAgent")
		self.time_limit_agent = TimeLimitAgent("TimeLimitAgent")
		self.limit_agent = LimitOrderAgent("LimitOrderAgent")

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

		# Get pre-sliced day data (already filtered to specific date by BacktestAgent)
		day_data = self.context.get("day_data") or {}
		if not day_data:
			self.logger.warning(f"No day data available for {trading_date}")

		journal = Journal(portfolio_name, context=self.context.__dict__)
		orders_mgr = Orders(portfolio_name, context=self.context.__dict__)

		# Execute buy orders in priority: limit orders first, then market orders
		buy_results = []

		# 1. Execute limit orders (these stay pending until price condition met)
		self.limit_agent.context = self.context
		limit_result = self.limit_agent.process({"day_data": day_data})
		buy_results.extend(limit_result.get("output", {}).get("orders", []))

		# 2. Execute market orders (remaining pending orders)
		market_results = self._execute_buy_orders(
			orders_mgr,
			journal,
			portfolio_name,
			trading_date,
			day_data
		)
		buy_results.extend(market_results)

		# Execute exit orders via subagents in sequence
		exit_results = []

		# 0. Update trailing stops (before checking stop losses)
		self.trailing_stop_agent.context = self.context
		trailing_stop_result = self.trailing_stop_agent.process({"day_data": day_data})
		self.logger.info(f"Trailing stops updated: {trailing_stop_result.get('output', {}).get('updated', 0)} positions")

		# 1. Stop loss exits
		self.stop_loss_agent.context = self.context
		stop_loss_result = self.stop_loss_agent.process({"day_data": day_data})
		exit_results.extend(stop_loss_result.get("output", {}).get("exits", []))

		# 2. Take profit exits (only if enabled in strategy)
		take_profit_enabled = self._is_take_profit_enabled()
		if take_profit_enabled:
			self.target_agent.context = self.context
			target_result = self.target_agent.process({"day_data": day_data})
			exit_results.extend(target_result.get("output", {}).get("exits", []))
		else:
			self.logger.info("Take profit is disabled in strategy, skipping target agent")

		# 3. Time limit exits
		self.time_limit_agent.context = self.context
		time_limit_result = self.time_limit_agent.process({"day_data": day_data})
		exit_results.extend(time_limit_result.get("output", {}).get("exits", []))

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
		day_data: Dict[str, Any]
	) -> List[Dict[str, Any]]:
		"""Execute pending BUY orders using market data.

		Args:
			orders_mgr: Orders manager
			journal: Journal for recording transactions
			portfolio_name: Portfolio name
			trading_date: Date of execution
			day_data: Pre-sliced market data {ticker: row} for the specific date

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
				execution_method = str(order_row.get("execution_method", "market"))

				# Skip limit orders (handled by LimitOrderAgent)
				if execution_method == "limit":
					continue

				quantity = int(order_row.get("quantity", 0))
				entry_price = float(order_row.get("entry_price", 0))
				stop_loss = float(order_row.get("stop_loss", 0)) if order_row.get("stop_loss") else None
				take_profit = float(order_row.get("take_profit", 0)) if order_row.get("take_profit") else None
				trailing_stop_distance = float(order_row.get("trailing_stop_distance", 0)) if order_row.get("trailing_stop_distance") else None

				# Get market price for the date (day_data is {ticker: row}, pre-sliced)
				market_price = self._get_market_price(ticker, day_data)
				if market_price is None:
					market_price = entry_price

				# Execute at better of entry_price or market price
				execution_price = min(market_price, entry_price)

				# Validate and adjust stop_loss/take_profit based on execution price
				# If order was created on a previous day, these values might be stale
				if stop_loss and stop_loss >= execution_price:
					# Stop loss is above execution price - recalculate based on risk ratio
					if take_profit and execution_price > 0:
						risk_ratio = (take_profit - entry_price) / (entry_price - stop_loss) if (entry_price - stop_loss) != 0 else 1.0
						# Recalculate stop_loss to maintain proper risk management
						stop_loss = execution_price * 0.97  # 3% below execution price as safe default
				if take_profit and take_profit <= execution_price:
					# Take profit is below or at execution price - recalculate
					take_profit = execution_price * 1.05  # 5% above execution price as safe default

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

					# Record BUY transaction in journal with stop loss, take profit, and trailing stop
					journal.add_transaction(
						operation="BUY",
						ticker=ticker,
						quantity=result.filled_quantity,
						price=result.filled_price,
						fees=0,
						stop_loss=stop_loss,
						take_profit=take_profit,
						trailing_stop_distance=trailing_stop_distance,
						highest_price=result.filled_price,
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

	def _is_take_profit_enabled(self) -> bool:
		"""Check if take_profit is enabled in strategy configuration.

		In backtest mode, reads strategy config from strategy_name in context.
		In paper trading mode, conservatively enables take_profit (allows TargetAgent to check).

		Returns:
			True if take_profit should be evaluated, False if disabled
		"""
		strategy_name = self.context.get("strategy_name")
		if not strategy_name:
			# No strategy context (e.g., paper trading) - allow target agent to run
			self.logger.debug("No strategy_name in context, enabling take_profit")
			return True

		try:
			from tools.strategy.strategy import StrategyManager
			manager = StrategyManager()
			result = manager.load_strategy(strategy_name)
			
			if result.get("status") != "success":
				self.logger.warning(f"Could not load strategy config for {strategy_name}, enabling take_profit")
				return True
			
			strategy_config = result.get("data", {})
			if not strategy_config:
				self.logger.warning(f"Empty strategy config for {strategy_name}, enabling take_profit")
				return True

			# Check if take_profit is explicitly disabled
			exit_params = strategy_config.get("exit", {}).get("parameters", {})
			take_profit = exit_params.get("take_profit", {})

			# If formula is 'False' (string) or False (bool), it's disabled
			formula = take_profit.get("formula")
			is_disabled = formula == "False" or formula is False
			
			self.logger.info(f"Strategy {strategy_name}: take_profit.formula={repr(formula)}, disabled={is_disabled}")
			
			if is_disabled:
				return False

			return True
		except Exception as e:
			self.logger.warning(f"Error checking take_profit enabled: {e}, assuming enabled")
			return True

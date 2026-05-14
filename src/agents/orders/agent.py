"""Orders agent for managing order lifecycle and expiration."""

from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
from core.agent import Agent
from tools.portfolio.orders import Orders
from tools.strategy.strategy import StrategyManager


class OrdersAgent(Agent):
	"""Manage order lifecycle and expire pending orders at end of trading day.

	Orders have a 1-day lifetime. Any pending order not executed by end of day
	is marked as expired. This agent runs in PostMarketFlow to clean up stale orders.
	"""

	def __init__(self, name: str = "OrdersAgent", context: Optional[Any] = None):
		"""Initialize orders agent.

		Args:
			name: Agent name
			context: AgentContext for shared state
		"""
		super().__init__(name, context)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Expire pending orders that exceeded their holding period.

		Args:
			input_data: Input data with:
				- portfolio_name: Portfolio name (optional, uses context if not provided)
				- holding_period: Holding period in days (optional, default 1 day)

		Returns:
			Response with expiration results
		"""
		if input_data is None:
			input_data = {}

		portfolio_name = input_data.get("portfolio_name") or self.context.get("portfolio_name") or "default"
		trading_date = self.context.get("date")

		# Get time_stop from strategy config (how long to wait for orders to fill before expiring)
		# Default 1 day - this is order expiration, separate from position holding_period
		time_stop = input_data.get("time_stop", 1)
		strategy_name = self.context.get("strategy_name")
		if strategy_name:
			try:
				strategy_manager = StrategyManager()
				strategy_result = strategy_manager.load_strategy(strategy_name)
				if strategy_result.get("status") == "success":
					strategy_data = strategy_result.get("data", {})
					exit_config = strategy_data.get("exit", {}).get("parameters", {})
					ts_formula = exit_config.get("time_stop", {}).get("formula")
					if ts_formula:
						try:
							time_stop = int(float(ts_formula))
						except (ValueError, TypeError):
							pass
			except Exception as e:
				self.logger.debug(f"Could not load strategy config for time_stop: {e}")

		if not trading_date:
			return {
				"status": "error",
				"message": "date not set in context",
				"output": {"expired_count": 0, "expired_orders": []},
			}

		orders_mgr = Orders(portfolio_name, context=self.context.__dict__)
		expired_results = self._expire_old_orders(orders_mgr, trading_date, time_stop)

		return {
			"status": "success",
			"output": {
				"expired_count": len(expired_results),
				"expired_orders": expired_results,
			},
			"message": f"Expired {len(expired_results)} pending order(s) with {time_stop}-day time_stop exceeded",
		}

	def _expire_old_orders(
		self,
		orders_mgr: Orders,
		trading_date: Any,
		time_stop: int = 1
	) -> List[Dict[str, Any]]:
		"""Expire pending orders that have exceeded their expiration_date.

		Rules:
		- BUY orders: expire after 1 calendar day (default)
		- SELL orders (exit conditions): expire after 1 calendar day (default)
		- SELL orders (linked SL/TP): expire after 365 days
		- Pending orders with expiration_date <= trading_date are expired
		- Already executed orders are left unchanged
		- Already cancelled/expired orders are left unchanged

		Args:
			orders_mgr: Orders manager
			trading_date: Current trading date
			time_stop: (deprecated, kept for backward compatibility)

		Returns:
			List of expired order results
		"""
		expired_results = []

		try:
			# Convert trading_date to date object if needed
			if hasattr(trading_date, 'date'):
				trading_date = trading_date.date()
			else:
				trading_date = datetime.fromisoformat(str(trading_date)).date()

			df = orders_mgr.load_df()
			if df.empty:
				return expired_results

			# Find all pending orders
			pending_mask = df["status"].str.upper() == "PENDING"
			pending_orders = df[pending_mask]

			if pending_orders.empty:
				self.logger.debug(
					f"No pending orders to expire. Total orders: {len(df)}, "
					f"Status breakdown: {df['status'].value_counts().to_dict()}"
				)
				return expired_results

			# Check expiration_date for each pending order
			for _, order in pending_orders.iterrows():
				order_id = str(order.get("id", ""))
				ticker = str(order.get("ticker", ""))
				quantity = int(order.get("quantity", 0))
				expiration_date_str = str(order.get("expiration_date", ""))
				operation = str(order.get("operation", "BUY")).upper()

				if not expiration_date_str:
					# Fallback: if no expiration_date, use old time_stop logic
					created_at_str = str(order.get("created_at", ""))
					try:
						created_datetime = datetime.fromisoformat(created_at_str)
						created_date = created_datetime.date()
						age_days = (trading_date - created_date).days
						if age_days >= time_stop:
							orders_mgr.update_order_status(order_id, "expired")
							expired_results.append({
								"order_id": order_id,
								"ticker": ticker,
								"quantity": quantity,
								"status": "expired",
								"reason": f"{time_stop}-day time_stop exceeded (fallback)",
							})
							self.logger.info(
								f"EXPIRED {operation} {ticker} x {quantity} order {order_id} (fallback)"
							)
					except (ValueError, AttributeError):
						self.logger.debug(f"Could not parse dates for order {order_id}")
					continue

				# Parse expiration_date
				try:
					expiration_datetime = datetime.fromisoformat(expiration_date_str)
					expiration_date = expiration_datetime.date()
				except (ValueError, AttributeError):
					self.logger.error(f"Could not parse expiration_date for order {order_id}: {expiration_date_str}")
					continue

				self.logger.debug(
					f"Order {order_id} ({operation} {ticker} x {quantity}): "
					f"expiration_date {expiration_date}, today {trading_date}"
				)

				# Expire if today >= expiration_date
				if trading_date >= expiration_date:
					orders_mgr.update_order_status(order_id, "expired")

					expired_results.append({
						"order_id": order_id,
						"ticker": ticker,
						"quantity": quantity,
						"operation": operation,
						"expiration_date": expiration_date.isoformat(),
						"status": "expired",
						"reason": f"Order expired (expiration_date {expiration_date} < {trading_date})",
					})

					self.logger.info(
						f"EXPIRED {operation} {ticker} x {quantity} order {order_id} "
						f"(expiration {expiration_date} < {trading_date})"
					)

		except Exception as e:
			self.logger.error(f"Error expiring old orders: {e}")

		return expired_results

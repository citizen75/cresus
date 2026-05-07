"""Order construction sub-agent for assembling final executable orders."""

from typing import Any, Dict, Optional
from datetime import datetime
import hashlib
from core.agent import Agent
from tools.strategy.strategy import StrategyManager
from tools.strategy.config_evaluator import ConfigEvaluator


class OrderConstructionAgent(Agent):
	"""Assemble final executable orders.

	Creates order objects with all parameters, metadata, and validation
	ready for handoff to execution layer.
	"""

	def __init__(self, name: str = "OrderConstructionAgent"):
		"""Initialize order construction agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Construct final orders from validated timing decisions.

		Reads strategy config for trailing_stop and holding_period,
		adds them to orders for use by post-market and exit logic.

		Args:
			input_data: Input data (optional)

		Returns:
			Response with executable orders
		"""
		if input_data is None:
			input_data = {}

		validated_orders = self.context.get("validated_orders") or []
		entry_recommendations = self.context.get("entry_recommendations") or []

		if not validated_orders:
			return {
				"status": "success",
				"input": input_data,
				"output": {"orders": []},
				"message": "No validated orders to construct"
			}

		# Try to load strategy config for entry and exit parameters
		strategy_name = self.context.get("strategy_name")
		exit_config = {}
		entry_config = {}

		if strategy_name:
			try:
				strategy_manager = StrategyManager()
				strategy_result = strategy_manager.load_strategy(strategy_name)
				if strategy_result.get("status") == "success":
					strategy_data = strategy_result.get("data", {})
					exit_config = strategy_data.get("exit", {}).get("parameters", {})
					entry_config = strategy_data.get("entry", {}).get("parameters", {})
			except Exception as e:
				self.logger.debug(f"Could not load strategy config: {e}")

		if strategy_name is None:
			strategy_name = "unknown"

		# Build recommendation lookup
		rec_lookup = {rec["ticker"]: rec for rec in entry_recommendations}

		# Construct executable orders
		orders = []
		for order in validated_orders:
			ticker = order.get("ticker")
			rec = rec_lookup.get(ticker, {})

			# Calculate risk/reward ratio
			entry_price = order.get("entry_price", 0)
			stop_loss = rec.get("stop_loss")
			take_profit = rec.get("take_profit")

			risk_reward = None
			if stop_loss and take_profit and entry_price:
				risk = abs(entry_price - stop_loss)
				reward = abs(take_profit - entry_price)
				if risk > 0:
					risk_reward = reward / risk

			# Extract trailing stop distance and holding period from config
			trailing_stop_distance = None
			holding_period = None

			# Calculate trailing_stop_distance based on the stop_loss
			# If trailing_stop is configured, the distance is (entry_price - initial_stop_loss)
			if "trailing_stop" in exit_config and stop_loss is not None and entry_price is not None:
				# The initial trailing distance is the distance from entry to the initial stop loss
				# This distance will be maintained as the price rises (hence "trailing")
				trailing_stop_distance = entry_price - stop_loss

			if "holding_period" in exit_config:
				hp_formula = exit_config["holding_period"].get("formula")
				if hp_formula:
					# Try to evaluate holding_period (usually a constant integer)
					try:
						holding_period = int(float(hp_formula))
					except (ValueError, TypeError):
						data_context = {"close": entry_price}
						result = ConfigEvaluator.evaluate_formula(hp_formula, data_context)
						if result:
							holding_period = int(result)

			# Determine execution method and limit price
			execution_method = order.get("execution_method", "market")
			limit_price = None

			# Check if entry config specifies limit orders
			if "limit_price" in entry_config:
				# Allow strategy to use limit orders
				lp_formula = entry_config["limit_price"].get("formula")
				if lp_formula:
					data_context = {
						"close": entry_price,
						"atr_14": rec.get("risk_amount", 0),
					}
					limit_price = ConfigEvaluator.evaluate_formula(lp_formula, data_context)
					if limit_price:
						execution_method = "limit"

			executable_order = {
				"id": self._generate_order_id(ticker),
				"ticker": ticker,
				"shares": order.get("shares"),
				"entry_price": entry_price,
				"limit_price": limit_price,
				"execution_method": execution_method,
				"limit_offset": order.get("limit_offset", 0),
				"scale_count": order.get("scale_count", 1),
				"stop_loss": stop_loss,
				"take_profit": take_profit,
				"trailing_stop_distance": trailing_stop_distance,
				"holding_period": holding_period,
				"risk_amount": order.get("risk_amount"),
				"risk_reward": risk_reward,
				"metadata": {
					"strategy": strategy_name,
					"entry_score": rec.get("entry_score", 0),
					"composite_score": rec.get("composite_score", 0),
					"rr_ratio": rec.get("rr_ratio", 0),
					"recommendation": rec.get("recommendation", "HOLD"),
					"timestamp": self._get_timestamp(),
				},
			}

			orders.append(executable_order)

		self.context.set("executable_orders", orders)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"orders": orders,
				"count": len(orders),
				"total_risk": sum(o["risk_amount"] for o in orders if o.get("risk_amount")),
			},
			"message": f"Constructed {len(orders)} executable orders"
		}

	def _generate_order_id(self, ticker: str) -> str:
		"""Generate unique order ID.

		Args:
			ticker: Ticker symbol

		Returns:
			Order ID
		"""
		timestamp = self._get_timestamp()
		id_str = f"{ticker}_{timestamp}"
		return hashlib.md5(id_str.encode()).hexdigest()[:12]

	def _get_timestamp(self) -> str:
		"""Get ISO timestamp - uses context date if set (for backtesting), otherwise current time.

		Returns:
			ISO timestamp string
		"""
		# Use context date if available (backtesting scenario)
		context_date = self.context.get("date")
		if context_date:
			if isinstance(context_date, str):
				return f"{context_date}T09:00:00.000000"  # Use 9 AM as trading day start
			else:
				return f"{context_date.isoformat()}T09:00:00.000000"

		# Fall back to current time
		return datetime.utcnow().isoformat()

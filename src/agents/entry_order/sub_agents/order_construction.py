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

		# Try to load strategy config for exit parameters
		strategy_name = self.context.get("strategy_name")
		exit_config = {}
		
		if strategy_name:
			try:
				strategy_manager = StrategyManager()
				strategy_result = strategy_manager.load_strategy(strategy_name)
				if strategy_result.get("status") == "success":
					strategy_data = strategy_result.get("data", {})
					exit_config = strategy_data.get("exit", {}).get("parameters", {})
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

			# Extract trailing_stop and holding_period from config
			trailing_stop = None
			holding_period = None

			if "trailing_stop" in exit_config:
				ts_formula = exit_config["trailing_stop"].get("formula")
				if ts_formula:
					# Evaluate trailing_stop formula (e.g., "data['close'] - data['atr_14']")
					data_context = {
						"close": entry_price,
						"atr_14": rec.get("risk_amount", 0),  # Use risk_amount as proxy for ATR
					}
					trailing_stop = ConfigEvaluator.evaluate_formula(ts_formula, data_context)

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

			executable_order = {
				"id": self._generate_order_id(ticker),
				"ticker": ticker,
				"shares": order.get("shares"),
				"entry_price": entry_price,
				"execution_method": order.get("execution_method", "market"),
				"limit_offset": order.get("limit_offset", 0),
				"scale_count": order.get("scale_count", 1),
				"stop_loss": stop_loss,
				"take_profit": take_profit,
				"trailing_stop": trailing_stop,
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

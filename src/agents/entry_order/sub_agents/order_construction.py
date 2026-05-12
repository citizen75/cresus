"""Order construction sub-agent for assembling final executable orders."""

from typing import Any, Dict, Optional
from datetime import datetime
import hashlib
from core.agent import Agent
from tools.strategy.strategy import StrategyManager
from tools.formula.numeric_evaluator import evaluate_numeric_formula


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

		Reads strategy config for stop loss and holding_period,
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

			# Calculate trailing_stop_distance if using trailing stop type
			# For fix stops, trailing_stop_distance is not needed (ExitAgent handles it)
			if "stop" in exit_config and entry_price is not None:
				stop_config = exit_config["stop"]
				stop_type = stop_config.get("type", "fix") if isinstance(stop_config, dict) else "fix"

				# Only calculate trailing_stop_distance for trailing stop type
				if stop_type == "trailing":
					# For trailing stops, distance is calculated as: entry_price - stop_level
					if isinstance(stop_config, dict) and "formula" in stop_config:
						stop_formula = stop_config.get("formula")
						if stop_formula:
							# Build evaluation context with entry price
							data_context = {
								"close": entry_price,
								"entry": entry_price,
							}

							# Try to evaluate the formula
							try:
								stop_level = evaluate_numeric_formula(stop_formula, data_context)
								if stop_level is not None:
									import math
									if not math.isnan(stop_level) and not math.isinf(stop_level):
										# Formula returns the stop level, distance is difference from entry
										trailing_stop_distance = entry_price - stop_level
							except Exception:
								# Fallback: use stop_loss-based distance if available
								if stop_loss is not None:
									trailing_stop_distance = entry_price - stop_loss
					elif stop_loss is not None:
						# Fallback: use stop_loss-based distance
						trailing_stop_distance = entry_price - stop_loss

			if "holding_period" in exit_config:
				hp_formula = exit_config["holding_period"].get("formula")
				if hp_formula:
					# Try to evaluate holding_period (usually a constant integer)
					try:
						import math
						hp_result = float(hp_formula)
						if not math.isnan(hp_result) and not math.isinf(hp_result):
							holding_period = int(hp_result)
					except (ValueError, TypeError):
						data_context = {"close": entry_price}
						result = evaluate_numeric_formula(hp_formula, data_context)
						if result:
							import math
							if not math.isnan(result) and not math.isinf(result):
								holding_period = int(result)

			# Determine execution method and limit price
			execution_method = order.get("execution_method", "market")
			limit_price = None
			limit_price_formula = None

			# Only calculate limit_price if execution_method is "limit"
			# Respect the execution_method set by EntryTimingAgent (from strategy order_type config)
			if execution_method == "limit" and "limit_price" in entry_config:
				# Calculate limit price for limit orders
				lp_formula = entry_config["limit_price"].get("formula")
				if lp_formula:
					# Store formula for later evaluation at execution time with fresh market data
					limit_price_formula = lp_formula
					# For now, use entry_price as placeholder - will be re-evaluated at execution
					data_context = {
						"close": entry_price,
						"atr_14": rec.get("risk_amount", 0),
					}
					limit_price = evaluate_numeric_formula(lp_formula, data_context)

			executable_order = {
				"id": self._generate_order_id(ticker),
				"ticker": ticker,
				"shares": order.get("shares"),
				"entry_price": entry_price,
				"limit_price": limit_price,
				"limit_price_formula": limit_price_formula,  # Store formula for re-evaluation at execution time
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

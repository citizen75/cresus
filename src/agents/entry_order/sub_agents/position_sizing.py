"""Position sizing sub-agent for calculating order sizes."""

from typing import Any, Dict, Optional
from core.agent import Agent
from tools.portfolio import PortfolioManager
from tools.data import Fundamental
from tools.strategy.strategy import StrategyManager
from tools.strategy.config_evaluator import ConfigEvaluator


class PositionSizingAgent(Agent):
	"""Calculate position size for each entry opportunity.

	Uses portfolio metrics and risk tolerance to determine shares/contracts
	for each trade based on selected sizing method.
	"""

	def __init__(self, name: str = "PositionSizingAgent", sizing_method: str = "fractional", risk_percent: float = 2.0):
		"""Initialize position sizing agent.

		Args:
			name: Agent name
			sizing_method: "fractional" (default), "kelly", or "volatility"
			risk_percent: Risk percentage of portfolio equity (default 2%)
		"""
		super().__init__(name)
		self.sizing_method = sizing_method
		self.risk_percent = risk_percent

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Calculate position sizes for entry recommendations.

		Uses strategy config position_size formula if available, otherwise
		falls back to portfolio-based sizing methods.

		Args:
			input_data: Input data (optional)

		Returns:
			Response with position sizing results
		"""
		if input_data is None:
			input_data = {}

		# Get portfolio and entry data from context
		portfolio_name = self.context.get("portfolio_name") or "default"
		entry_recommendations = self.context.get("entry_recommendations") or []

		if not entry_recommendations:
			return {
				"status": "success",
				"input": input_data,
				"output": {},
				"message": "No entry recommendations to size"
			}

		# Try to load strategy config for position sizing formula
		strategy_name = self.context.get("strategy_name") if self.context else None
		position_size_formula = None

		if strategy_name:
			try:
				strategy_manager = StrategyManager()
				strategy_result = strategy_manager.load_strategy(strategy_name)
				if strategy_result.get("status") == "success":
					strategy_data = strategy_result.get("data", {})
					entry_config = strategy_data.get("entry", {}).get("parameters", {})
					if "position_size" in entry_config:
						position_size_formula = entry_config["position_size"].get("formula")
						if position_size_formula:
							self.logger.info(f"Using position_size formula from strategy: {position_size_formula}")
			except Exception as e:
				self.logger.debug(f"Could not load strategy config: {e}")

		# Get portfolio metrics
		pm = PortfolioManager(context=self.context.__dict__)
		portfolio_details = pm.get_portfolio_details(portfolio_name)
		cash = pm.get_portfolio_cash(portfolio_name)

		if not portfolio_details:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Portfolio '{portfolio_name}' not found"
			}

		# Calculate position sizes
		sized_orders = []
		for rec in entry_recommendations:
			ticker = rec.get("ticker")
			entry_price = rec.get("entry_price")
			stop_loss = rec.get("stop_loss")

			if not ticker or entry_price is None or stop_loss is None:
				continue

			# Skip if entry_price or stop_loss are invalid
			try:
				entry_price = float(entry_price)
				stop_loss = float(stop_loss)
			except (ValueError, TypeError):
				self.logger.debug(f"{ticker}: Invalid entry_price or stop_loss, skipping")
				continue

			# Get current price
			fundamental = Fundamental(ticker)
			current_price = fundamental.get_current_price() or entry_price

			# Try to calculate position size from strategy config formula first
			shares = None
			if position_size_formula:
				data_context = {"close": current_price}
				shares = ConfigEvaluator.evaluate_position_size(
					position_size_formula, data_context, max_shares=None
				)
				if shares and shares > 0:
					self.logger.debug(f"{ticker}: Using formula-based shares={shares}")

			# Fall back to portfolio-based sizing if formula didn't work
			if not shares or shares <= 0:
				# Calculate position size based on method
				if self.sizing_method == "fractional":
					shares = self._fractional_sizing(cash, current_price, entry_price, stop_loss)
				elif self.sizing_method == "kelly":
					rr_ratio = rec.get("rr_ratio", 1.0)
					win_rate = self.context.get("win_rate", 0.5)
					shares = self._kelly_sizing(cash, current_price, rr_ratio, win_rate)
				elif self.sizing_method == "volatility":
					volatility = rec.get("volatility", 0.02)
					shares = self._volatility_sizing(cash, current_price, volatility)
				else:
					shares = self._fractional_sizing(cash, current_price, entry_price, stop_loss)

			# Validate shares is a valid number
			import math
			if shares is not None and not math.isnan(shares) and not math.isinf(shares) and shares > 0:
				try:
					shares_int = int(shares)
					sized_orders.append({
						"ticker": ticker,
						"shares": shares_int,
						"entry_price": entry_price,
						"order_value": shares_int * current_price,
						"risk_amount": abs(shares_int * (entry_price - stop_loss)),
						"sizing_method": "strategy_config" if position_size_formula else self.sizing_method,
					})
				except (ValueError, TypeError) as e:
					self.logger.debug(f"{ticker}: Failed to convert shares to int: {e}, skipping")
					continue

		# Store sized orders in context
		self.context.set("sized_orders", sized_orders)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"sized": len(sized_orders),
				"total_order_value": sum(o["order_value"] for o in sized_orders),
				"total_risk": sum(o["risk_amount"] for o in sized_orders),
			},
			"message": f"Sized {len(sized_orders)} entry positions"
		}

	def _fractional_sizing(self, cash: float, current_price: float, entry_price: float, stop_loss: float) -> int:
		"""Calculate shares using fixed fractional method.

		Risk a fixed percent of portfolio per trade, but limit to 5% of cash per position.

		Args:
			cash: Available cash
			current_price: Current price
			entry_price: Entry price
			stop_loss: Stop loss price

		Returns:
			Number of shares to trade
		"""
		import math
		
		# Validate inputs
		if math.isnan(current_price) or math.isnan(entry_price) or math.isnan(stop_loss):
			return 0
		if math.isinf(current_price) or math.isinf(entry_price) or math.isinf(stop_loss):
			return 0
		if current_price <= 0 or cash <= 0:
			return 0
			
		risk_amount = cash * (self.risk_percent / 100.0)
		price_risk = abs(entry_price - stop_loss)

		if price_risk <= 0:
			return 0

		# Calculate shares based on risk amount
		shares = risk_amount / price_risk

		# Limit position to 5% of available cash (conservative)
		max_position_value = cash * 0.05
		max_shares = int(max_position_value / current_price)

		# Final check before returning
		result = min(shares, max_shares)
		if math.isnan(result) or math.isinf(result):
			return 0
		return int(result)

	def _kelly_sizing(self, cash: float, current_price: float, rr_ratio: float, win_rate: float) -> int:
		"""Calculate shares using Kelly Criterion.

		Args:
			cash: Available cash
			current_price: Current price
			rr_ratio: Risk/reward ratio
			win_rate: Historical win rate (0-1)

		Returns:
			Number of shares to trade
		"""
		import math
		
		# Validate inputs
		if math.isnan(current_price) or math.isnan(rr_ratio) or math.isnan(win_rate):
			return 0
		if math.isinf(current_price) or math.isinf(rr_ratio) or math.isinf(win_rate):
			return 0
		if current_price <= 0 or cash <= 0:
			return 0
			
		if rr_ratio <= 0 or win_rate <= 0:
			return 0

		# Kelly formula: f = (bp - q) / b
		# where b = rr_ratio, p = win_rate, q = 1 - win_rate
		kelly_fraction = (rr_ratio * win_rate - (1 - win_rate)) / rr_ratio

		# Use half-Kelly for safety
		kelly_fraction = max(0, kelly_fraction * 0.5)

		# Limit to max 25% of portfolio per trade
		kelly_fraction = min(kelly_fraction, 0.25)

		shares = (cash * kelly_fraction) / current_price
		result = shares
		if math.isnan(result) or math.isinf(result):
			return 0
		return int(result)

	def _volatility_sizing(self, cash: float, current_price: float, volatility: float) -> int:
		"""Calculate shares using volatility-adjusted sizing.

		Higher volatility = smaller position size.

		Args:
			cash: Available cash
			current_price: Current price
			volatility: Volatility measure (0-1)

		Returns:
			Number of shares to trade
		"""
		import math
		
		# Validate inputs
		if math.isnan(current_price) or math.isnan(volatility):
			return 0
		if math.isinf(current_price) or math.isinf(volatility):
			return 0
		if current_price <= 0 or cash <= 0:
			return 0
			
		# Adjust risk percent inversely with volatility
		base_risk = self.risk_percent / 100.0
		adjusted_risk = base_risk / (1 + volatility * 10)
		adjusted_risk = max(adjusted_risk, 0.005)  # Min 0.5%

		shares = (cash * adjusted_risk) / current_price
		result = shares
		if math.isnan(result) or math.isinf(result):
			return 0
		return int(result)

"""Position sizing sub-agent for calculating order sizes."""

from typing import Any, Dict, Optional
from core.agent import Agent
from tools.portfolio import PortfolioManager
from tools.data import Fundamental


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

		Reads entry_recommendations from context and calculates shares
		based on portfolio cash and risk tolerance.

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

			if not ticker or not entry_price or not stop_loss:
				continue

			# Get current price
			fundamental = Fundamental(ticker)
			current_price = fundamental.get_current_price() or entry_price

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

			if shares > 0:
				sized_orders.append({
					"ticker": ticker,
					"shares": int(shares),
					"entry_price": entry_price,
					"order_value": int(shares) * current_price,
					"risk_amount": abs(int(shares) * (entry_price - stop_loss)),
					"sizing_method": self.sizing_method,
				})

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
		risk_amount = cash * (self.risk_percent / 100.0)
		price_risk = abs(entry_price - stop_loss)

		if price_risk <= 0:
			return 0

		# Calculate shares based on risk amount
		shares = risk_amount / price_risk

		# Limit position to 5% of available cash (conservative)
		max_position_value = cash * 0.05
		max_shares = int(max_position_value / current_price)

		return int(min(shares, max_shares))

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
		return int(shares)

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
		# Adjust risk percent inversely with volatility
		base_risk = self.risk_percent / 100.0
		adjusted_risk = base_risk / (1 + volatility * 10)
		adjusted_risk = max(adjusted_risk, 0.005)  # Min 0.5%

		shares = (cash * adjusted_risk) / current_price
		return int(shares)

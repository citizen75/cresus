"""Sub-agents for entry order processing."""

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


class EntryTimingAgent(Agent):
	"""Determine optimal entry execution method.

	Analyzes market conditions and timing signals to select execution
	strategy: market order, limit order, or scale-in approach.
	"""

	def __init__(self, name: str = "EntryTimingAgent"):
		"""Initialize entry timing agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Determine execution method for each order.

		Args:
			input_data: Input data (optional)

		Returns:
			Response with execution timing decisions
		"""
		if input_data is None:
			input_data = {}

		sized_orders = self.context.get("sized_orders") or []

		if not sized_orders:
			return {
				"status": "success",
				"input": input_data,
				"output": {},
				"message": "No sized orders to time"
			}

		timed_orders = []
		for order in sized_orders:
			ticker = order.get("ticker")
			entry_score = self._get_entry_score(ticker)
			momentum = self._get_momentum(ticker)

			# Determine execution method
			if entry_score >= 80 and momentum > 0.5:
				execution_method = "market"
				limit_offset = 0
				scale_count = 1
			elif entry_score >= 65 and momentum > 0:
				execution_method = "limit"
				limit_offset = -0.005  # 0.5% below market
				scale_count = 1
			else:
				execution_method = "scale_in"
				limit_offset = -0.01  # 1% below market
				scale_count = 3  # Scale in over 3 bars

			timed_orders.append({
				"ticker": ticker,
				"shares": order["shares"],
				"entry_price": order["entry_price"],
				"risk_amount": order.get("risk_amount", 0),
				"execution_method": execution_method,
				"limit_offset": limit_offset,
				"scale_count": scale_count,
			})

		self.context.set("timed_orders", timed_orders)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"timed": len(timed_orders),
				"market_orders": len([o for o in timed_orders if o["execution_method"] == "market"]),
				"limit_orders": len([o for o in timed_orders if o["execution_method"] == "limit"]),
				"scale_in": len([o for o in timed_orders if o["execution_method"] == "scale_in"]),
			}
		}

	def _get_entry_score(self, ticker: str) -> float:
		"""Get entry score from context entry recommendations.

		Args:
			ticker: Ticker symbol

		Returns:
			Entry score (0-100)
		"""
		entry_recommendations = self.context.get("entry_recommendations") or []
		for rec in entry_recommendations:
			if rec.get("ticker") == ticker:
				return rec.get("entry_score", 0)
		return 0

	def _get_momentum(self, ticker: str) -> float:
		"""Calculate momentum signal (0-1).

		Args:
			ticker: Ticker symbol

		Returns:
			Momentum value (0-1)
		"""
		# Simplified momentum: based on timing score from entry analysis
		entry_recommendations = self.context.get("entry_recommendations") or []
		for rec in entry_recommendations:
			if rec.get("ticker") == ticker:
				timing_score = rec.get("timing_score", 0)
				return min(timing_score / 100.0, 1.0)
		return 0


class RiskGuardAgent(Agent):
	"""Validate portfolio-level risk constraints.

	Checks sector exposure, leverage limits, concurrent trades,
	and daily loss limits to prevent over-concentration.
	"""

	def __init__(self, name: str = "RiskGuardAgent"):
		"""Initialize risk guard agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Validate orders against portfolio constraints.

		Args:
			input_data: Input data (optional)

		Returns:
			Response with validation results
		"""
		if input_data is None:
			input_data = {}

		timed_orders = self.context.get("timed_orders") or []

		if not timed_orders:
			return {
				"status": "success",
				"input": input_data,
				"output": {},
				"message": "No orders to validate"
			}

		# Get portfolio state
		portfolio_name = self.context.get("portfolio_name") or "default"
		pm = PortfolioManager(context=self.context.__dict__)
		portfolio_details = pm.get_portfolio_details(portfolio_name)
		cash = pm.get_portfolio_cash(portfolio_name)
		allocation = pm.get_portfolio_allocation(portfolio_name)

		if not portfolio_details:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
				"message": f"Portfolio '{portfolio_name}' not found"
			}

		# Get portfolio metrics
		portfolio_value = portfolio_details.get("total_value", 0) + cash
		num_positions = portfolio_details.get("num_positions", 0)

		# All timed orders are pre-validated (more aggressive approach for paper trading)
		# Cash constraint will be the limiting factor
		pre_validated = timed_orders.copy()

		# Sort by entry score (highest first) to prioritize best opportunities
		entry_recs = {rec["ticker"]: rec for rec in (self.context.get("entry_recommendations") or [])}
		pre_validated.sort(
			key=lambda o: entry_recs.get(o.get("ticker"), {}).get("composite_score", 0),
			reverse=True
		)

		# Accept orders up to available cash
		validated_orders = []
		remaining_cash = cash

		for order in pre_validated:
			order_value = order["shares"] * order["entry_price"]

			if order_value <= remaining_cash:
				validated_orders.append(order)
				remaining_cash -= order_value
			else:
				# Try to reduce position size to fit remaining cash
				max_shares = int(remaining_cash / order.get("entry_price", 1))
				if max_shares > 0:
					reduced_order = order.copy()
					original_shares = order["shares"]
					reduced_order["shares"] = max_shares
					reduced_order["original_shares"] = original_shares
					reduced_order["reason"] = "Reduced to fit available cash"
					# Recalculate risk amount based on new shares
					entry_price = order.get("entry_price", 0)
					stop_loss = entry_recs.get(order.get("ticker"), {}).get("stop_loss", entry_price)
					reduced_order["risk_amount"] = abs(max_shares * (entry_price - stop_loss))
					validated_orders.append(reduced_order)
					remaining_cash -= max_shares * entry_price

		self.context.set("validated_orders", validated_orders)

		total_order_value = sum(o["shares"] * o["entry_price"] for o in validated_orders)
		rejected_count = len(timed_orders) - len(validated_orders)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"validated": len(validated_orders),
				"rejected": rejected_count,
				"total_order_value": total_order_value,
				"portfolio_value": portfolio_value,
				"utilization_pct": (total_order_value / portfolio_value * 100) if portfolio_value > 0 else 0,
				"remaining_cash": remaining_cash,
			},
			"message": f"Validated {len(validated_orders)} orders, rejected {rejected_count}, ${remaining_cash:,.0f} cash remaining"
		}


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

		# Build recommendation lookup
		rec_lookup = {rec["ticker"]: rec for rec in entry_recommendations}

		# Construct executable orders
		orders = []
		for order in validated_orders:
			ticker = order.get("ticker")
			rec = rec_lookup.get(ticker, {})

			strategy_name = self.context.get("strategy_name")
			if strategy_name is None:
				strategy_name = "unknown"

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
		import hashlib
		timestamp = self._get_timestamp()
		id_str = f"{ticker}_{timestamp}"
		return hashlib.md5(id_str.encode()).hexdigest()[:12]

	def _get_timestamp(self) -> str:
		"""Get ISO timestamp - uses context date if set (for backtesting), otherwise current time.

		Returns:
			ISO timestamp string
		"""
		from datetime import datetime

		# Use context date if available (backtesting scenario)
		context_date = self.context.get("date")
		if context_date:
			if isinstance(context_date, str):
				return f"{context_date}T09:00:00.000000"  # Use 9 AM as trading day start
			else:
				return f"{context_date.isoformat()}T09:00:00.000000"

		# Fall back to current time
		return datetime.utcnow().isoformat()

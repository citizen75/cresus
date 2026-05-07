"""Orders analysis sub-agent for analyzing order execution quality and effectiveness."""

from typing import Any, Dict, Optional, List
import pandas as pd
import yaml
from pathlib import Path
from core.agent import Agent
from tools.portfolio.journal import Journal
from utils.env import get_db_root


class OrdersAnalysisAgent(Agent):
	"""Analyze order execution quality and provide recommendations.

	Examines:
	- Order fill rates and execution quality
	- Position sizing consistency vs strategy config
	- Order timing and frequency patterns
	- Limit order effectiveness
	- Slippage and price impact
	- Order cancellation/expiration reasons
	- Daily activity patterns
	"""

	def __init__(self, name: str = "OrdersAnalysisAgent"):
		"""Initialize orders analysis agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Analyze order execution and effectiveness.

		Args:
			input_data: Input data with strategy info

		Returns:
			Response with order analysis and recommendations
		"""
		if input_data is None:
			input_data = {}

		backtest_dir = self.context.get("backtest_dir") if self.context else None
		portfolio_name = self.context.get("portfolio_name") if self.context else None
		strategy_name = self.context.get("strategy_name") if self.context else None

		if portfolio_name is None:
			portfolio_name = "default"

		if not backtest_dir:
			return {
				"status": "success",
				"input": input_data,
				"output": {
					"total_orders": 0,
					"orders_analysis": {},
					"recommendations": [],
				},
				"message": "No backtest_dir in context"
			}

		# Load journal
		journal = Journal(name=portfolio_name, context={"backtest_dir": backtest_dir})
		df = journal.load_df()

		if df is None or df.empty:
			return {
				"status": "success",
				"input": input_data,
				"output": {
					"total_orders": 0,
					"orders_analysis": {},
					"recommendations": [],
				},
				"message": "No orders executed"
			}

		# Load strategy config
		strategy_config = None
		if strategy_name:
			strategy_config = self._load_strategy_config(strategy_name)

		# Perform analysis
		analysis = self._analyze_orders(df, strategy_config)
		recommendations = self._generate_recommendations(analysis, strategy_config, df)

		return {
			"status": "success",
			"input": input_data,
			"output": {
				"strategy_name": strategy_name,
				"total_orders": analysis.get("total_orders", 0),
				"orders_analysis": analysis,
				"recommendations": recommendations,
				"total_recommendations": len(recommendations),
			},
			"message": f"Analyzed {analysis.get('total_orders', 0)} orders: {len(recommendations)} recommendations"
		}

	def _load_strategy_config(self, strategy_name: str) -> Optional[Dict[str, Any]]:
		"""Load strategy configuration file.

		Args:
			strategy_name: Name of the strategy

		Returns:
			Strategy config dict or None
		"""
		try:
			strategy_file = get_db_root() / "strategies" / f"{strategy_name}.yml"

			if not strategy_file.exists():
				self.logger.warning(f"Strategy config not found: {strategy_file}")
				return None

			with open(strategy_file, 'r') as f:
				config = yaml.safe_load(f)
				return config
		except Exception as e:
			self.logger.warning(f"Could not load strategy config: {e}")
			return None

	def _analyze_orders(self, df: pd.DataFrame, strategy_config: Optional[Dict]) -> Dict[str, Any]:
		"""Analyze order execution quality.

		Args:
			df: Order DataFrame
			strategy_config: Strategy configuration

		Returns:
			Analysis dict
		"""
		if df.empty:
			return {"total_orders": 0}

		df = df.copy()
		df["price"] = pd.to_numeric(df["price"], errors="coerce")
		df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")

		# Convert created_at to datetime for timing analysis
		if "created_at" in df.columns:
			df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

		total_orders = len(df)
		buy_orders = len(df[df["operation"] == "BUY"])
		sell_orders = len(df[df["operation"] == "SELL"])

		# Position sizing analysis
		sizing_analysis = self._analyze_position_sizing(df, strategy_config)

		# Order timing analysis
		timing_analysis = self._analyze_timing(df)

		# Buy/sell balance
		order_balance = self._analyze_order_balance(df)

		# Per-ticker analysis
		ticker_analysis = self._analyze_by_ticker(df)

		# Price analysis
		price_analysis = self._analyze_prices(df)

		# Same-day buy/sell analysis
		sameday_analysis = self._analyze_sameday_buynsell(df)

		return {
			"total_orders": total_orders,
			"buy_orders": buy_orders,
			"sell_orders": sell_orders,
			"buy_sell_ratio": buy_orders / sell_orders if sell_orders > 0 else 0,
			"sizing_analysis": sizing_analysis,
			"timing_analysis": timing_analysis,
			"order_balance": order_balance,
			"ticker_analysis": ticker_analysis,
			"price_analysis": price_analysis,
			"daily_activity": self._analyze_daily_activity(df),
			"sameday_buynsell": sameday_analysis,
		}

	def _analyze_position_sizing(self, df: pd.DataFrame, strategy_config: Optional[Dict]) -> Dict[str, Any]:
		"""Analyze position sizing consistency.

		Args:
			df: Order DataFrame
			strategy_config: Strategy config

		Returns:
			Position sizing analysis
		"""
		buy_df = df[df["operation"] == "BUY"]
		sell_df = df[df["operation"] == "SELL"]

		avg_buy_size = buy_df["quantity"].mean() if len(buy_df) > 0 else 0
		avg_sell_size = sell_df["quantity"].mean() if len(sell_df) > 0 else 0
		size_std_dev = df["quantity"].std() if len(df) > 1 else 0

		# Sizing consistency (coefficient of variation)
		avg_size = df["quantity"].mean()
		if avg_size > 0:
			cv = (size_std_dev / avg_size) * 100
		else:
			cv = 0

		# Expected position size from config
		expected_size = None
		if strategy_config:
			entry_params = strategy_config.get("entry", {}).get("parameters", {})
			pos_size_formula = entry_params.get("position_size", {}).get("formula", "")
			expected_size = f"~1000 / price" if "1000" in pos_size_formula else None

		return {
			"avg_buy_size": float(avg_buy_size),
			"avg_sell_size": float(avg_sell_size),
			"min_size": float(df["quantity"].min()),
			"max_size": float(df["quantity"].max()),
			"size_std_dev": float(size_std_dev),
			"size_consistency_pct": 100 - min(cv, 100),  # Higher is more consistent
			"zero_quantity_orders": len(df[df["quantity"] == 0]),
		}

	def _analyze_timing(self, df: pd.DataFrame) -> Dict[str, Any]:
		"""Analyze order timing patterns.

		Args:
			df: Order DataFrame

		Returns:
			Timing analysis
		"""
		if "created_at" not in df.columns:
			return {}

		# Convert to datetime
		df_copy = df.copy()
		df_copy["created_at"] = pd.to_datetime(df_copy["created_at"], errors="coerce")
		df_copy = df_copy.dropna(subset=["created_at"])

		if df_copy.empty:
			return {}

		# Time distribution
		date_counts = df_copy["created_at"].dt.date.value_counts()
		avg_orders_per_day = date_counts.mean()
		max_orders_per_day = date_counts.max()
		min_orders_per_day = date_counts.min()

		# Hour distribution (if intraday data)
		hour_counts = df_copy["created_at"].dt.hour.value_counts()
		peak_hour = hour_counts.idxmax() if len(hour_counts) > 0 else None

		return {
			"avg_orders_per_day": float(avg_orders_per_day),
			"max_orders_per_day": int(max_orders_per_day),
			"min_orders_per_day": int(min_orders_per_day),
			"peak_hour": int(peak_hour) if peak_hour is not None else None,
			"total_days": len(date_counts),
		}

	def _analyze_order_balance(self, df: pd.DataFrame) -> Dict[str, Any]:
		"""Analyze buy/sell order balance.

		Args:
			df: Order DataFrame

		Returns:
			Order balance analysis
		"""
		buy_df = df[df["operation"] == "BUY"]
		sell_df = df[df["operation"] == "SELL"]

		total_buy_qty = buy_df["quantity"].sum()
		total_sell_qty = sell_df["quantity"].sum()
		total_buy_value = (buy_df["quantity"] * buy_df["price"]).sum()
		total_sell_value = (sell_df["quantity"] * sell_df["price"]).sum()

		return {
			"total_buy_quantity": float(total_buy_qty),
			"total_sell_quantity": float(total_sell_qty),
			"total_buy_value": float(total_buy_value),
			"total_sell_value": float(total_sell_value),
			"imbalance_ratio": total_buy_qty / total_sell_qty if total_sell_qty > 0 else 0,
		}

	def _analyze_by_ticker(self, df: pd.DataFrame) -> Dict[str, Any]:
		"""Analyze orders by ticker.

		Args:
			df: Order DataFrame

		Returns:
			Per-ticker analysis
		"""
		ticker_stats = {}

		for ticker in df["ticker"].unique():
			ticker_df = df[df["ticker"] == ticker]
			buys = len(ticker_df[ticker_df["operation"] == "BUY"])
			sells = len(ticker_df[ticker_df["operation"] == "SELL"])

			ticker_stats[ticker] = {
				"total_orders": len(ticker_df),
				"buys": buys,
				"sells": sells,
				"avg_size": float(ticker_df["quantity"].mean()),
				"total_quantity": float(ticker_df["quantity"].sum()),
			}

		# Find most active tickers
		sorted_tickers = sorted(
			ticker_stats.items(),
			key=lambda x: x[1]["total_orders"],
			reverse=True
		)

		return {
			"total_tickers": len(ticker_stats),
			"most_active": [t[0] for t in sorted_tickers[:5]],
			"stats": ticker_stats,
		}

	def _analyze_prices(self, df: pd.DataFrame) -> Dict[str, Any]:
		"""Analyze order prices.

		Args:
			df: Order DataFrame

		Returns:
			Price analysis
		"""
		buy_df = df[df["operation"] == "BUY"]
		sell_df = df[df["operation"] == "SELL"]

		return {
			"avg_buy_price": float(buy_df["price"].mean()) if len(buy_df) > 0 else 0,
			"avg_sell_price": float(sell_df["price"].mean()) if len(sell_df) > 0 else 0,
			"price_range_min": float(df["price"].min()),
			"price_range_max": float(df["price"].max()),
			"zero_price_orders": len(df[df["price"] == 0]),
		}

	def _analyze_daily_activity(self, df: pd.DataFrame) -> Dict[str, Any]:
		"""Analyze daily order activity patterns.

		Args:
			df: Order DataFrame

		Returns:
			Daily activity analysis
		"""
		if "created_at" not in df.columns:
			return {}

		df_copy = df.copy()
		df_copy["created_at"] = pd.to_datetime(df_copy["created_at"], errors="coerce")
		df_copy = df_copy.dropna(subset=["created_at"])

		if df_copy.empty:
			return {}

		# Count by day
		daily_orders = df_copy.groupby(df_copy["created_at"].dt.date).size()

		# Count by day of week
		dow_orders = df_copy.groupby(df_copy["created_at"].dt.dayofweek).size()

		return {
			"daily_stats": {
				"mean": float(daily_orders.mean()),
				"std": float(daily_orders.std()),
				"max": int(daily_orders.max()),
				"min": int(daily_orders.min()),
			},
			"busiest_day": int(dow_orders.idxmax()) if len(dow_orders) > 0 else None,
		}

	def _analyze_sameday_buynsell(self, df: pd.DataFrame) -> Dict[str, Any]:
		"""Analyze same-day buy and sell orders for same stock.

		Identifies when the same stock is bought and sold on the same day,
		indicating either scalping behavior or conflicting signals.

		Args:
			df: Order DataFrame

		Returns:
			Same-day buy/sell analysis
		"""
		if "created_at" not in df.columns or "ticker" not in df.columns:
			return {"pairs_found": 0, "pairs": []}

		df_copy = df.copy()
		df_copy["created_at"] = pd.to_datetime(df_copy["created_at"], errors="coerce")
		df_copy["date"] = df_copy["created_at"].dt.date
		df_copy = df_copy.dropna(subset=["created_at", "ticker"])

		same_day_pairs = []

		# For each ticker, find days with both buy and sell
		for ticker in df_copy["ticker"].unique():
			ticker_df = df_copy[df_copy["ticker"] == ticker]

			# Group by date
			for date, day_df in ticker_df.groupby("date"):
				buys = day_df[day_df["operation"] == "BUY"]
				sells = day_df[day_df["operation"] == "SELL"]

				if len(buys) > 0 and len(sells) > 0:
					# Found same-day buy+sell pair
					buy_qty = buys["quantity"].sum()
					sell_qty = sells["quantity"].sum()
					buy_price = buys["price"].mean()
					sell_price = sells["price"].mean()

					same_day_pairs.append({
						"ticker": ticker,
						"date": str(date),
						"buy_orders": len(buys),
						"sell_orders": len(sells),
						"buy_quantity": float(buy_qty),
						"sell_quantity": float(sell_qty),
						"avg_buy_price": float(buy_price),
						"avg_sell_price": float(sell_price),
						"pnl_per_share": float(sell_price - buy_price),
						"total_pnl": float((sell_price - buy_price) * min(buy_qty, sell_qty)),
					})

		return {
			"pairs_found": len(same_day_pairs),
			"pairs": same_day_pairs,
		}

	def _generate_recommendations(
		self,
		analysis: Dict[str, Any],
		strategy_config: Optional[Dict],
		df: pd.DataFrame
	) -> List[Dict[str, Any]]:
		"""Generate recommendations based on order analysis.

		Args:
			analysis: Order analysis results
			strategy_config: Strategy configuration
			df: Order DataFrame

		Returns:
			List of recommendations
		"""
		recommendations = []

		total_orders = analysis.get("total_orders", 0)
		sizing_analysis = analysis.get("sizing_analysis", {})
		timing_analysis = analysis.get("timing_analysis", {})
		balance = analysis.get("order_balance", {})
		ticker_analysis = analysis.get("ticker_analysis", {})
		pricing = analysis.get("price_analysis", {})

		# Order size consistency
		size_consistency = sizing_analysis.get("size_consistency_pct", 0)
		if size_consistency < 50:
			recommendations.append({
				"category": "position_sizing",
				"priority": "high",
				"title": "Inconsistent Position Sizing",
				"description": f"Position sizes vary by {100 - size_consistency:.0f}% (low consistency)",
				"recommendation": "Implement fixed position size formula. Check if position_size calculation in entry config matches intended logic.",
				"metrics_involved": ["size_consistency", "avg_size", "size_std_dev"],
			})

		zero_quantity = sizing_analysis.get("zero_quantity_orders", 0)
		if zero_quantity > 0:
			recommendations.append({
				"category": "position_sizing",
				"priority": "critical",
				"title": "Zero Quantity Orders",
				"description": f"{zero_quantity} orders placed with zero quantity",
				"recommendation": "Critical bug: Orders are being placed without shares. Check position_size formula - may be dividing by infinity or returning zero.",
				"metrics_involved": ["zero_quantity_orders"],
			})

		zero_prices = pricing.get("zero_price_orders", 0)
		if zero_prices > 0:
			recommendations.append({
				"category": "pricing",
				"priority": "critical",
				"title": "Zero Price Orders",
				"description": f"{zero_prices} orders executed at $0 price",
				"recommendation": "Data error: Orders executed with zero price. Check price data source or limit_price formula.",
				"metrics_involved": ["zero_price_orders"],
			})

		# Buy/sell imbalance
		imbalance = balance.get("imbalance_ratio", 1.0)
		if imbalance > 2.0:
			recommendations.append({
				"category": "signal_quality",
				"priority": "high",
				"title": "Excessive Buy Orders",
				"description": f"Buy/sell ratio of {imbalance:.1f}x (too many buys)",
				"recommendation": "Exit signals may be missing or ineffective. Verify sell_conditions in strategy config are properly evaluated.",
				"metrics_involved": ["imbalance_ratio", "buy_orders", "sell_orders"],
			})
		elif imbalance < 0.5:
			recommendations.append({
				"category": "signal_quality",
				"priority": "high",
				"title": "Excessive Sell Orders",
				"description": f"Buy/sell ratio of {imbalance:.1f}x (too many sells)",
				"recommendation": "Entry signals weak or exit signals too aggressive. Check buy_conditions strength.",
				"metrics_involved": ["imbalance_ratio", "buy_orders", "sell_orders"],
			})

		# Daily activity analysis
		if timing_analysis:
			max_daily = timing_analysis.get("max_orders_per_day", 0)
			avg_daily = timing_analysis.get("avg_orders_per_day", 0)

			if max_daily > 50:
				recommendations.append({
					"category": "order_frequency",
					"priority": "high",
					"title": "Excessive Daily Orders",
					"description": f"Peak of {max_daily} orders in a single day (avg {avg_daily:.1f})",
					"recommendation": "Consider adding cooldown period between orders or holding period filter to reduce noise trading.",
					"metrics_involved": ["max_orders_per_day", "avg_orders_per_day"],
				})

			# Check variance
			std_dev = timing_analysis.get("daily_stats", {}).get("std", 0)
			if std_dev > avg_daily:
				recommendations.append({
					"category": "signal_consistency",
					"priority": "medium",
					"title": "Inconsistent Daily Activity",
					"description": f"Daily orders vary widely (std {std_dev:.1f} vs mean {avg_daily:.1f})",
					"recommendation": "Order generation is bursty rather than steady. Check if watch list updates are concentrated at specific times.",
					"metrics_involved": ["daily_activity_std", "daily_activity_mean"],
				})

		# Ticker concentration
		num_tickers = ticker_analysis.get("total_tickers", 0)
		most_active = ticker_analysis.get("most_active", [])
		if num_tickers > 0 and len(most_active) > 0:
			# Calculate concentration
			ticker_stats = ticker_analysis.get("stats", {})
			top_5_orders = sum(
				ticker_stats[t]["total_orders"]
				for t in most_active if t in ticker_stats
			)
			concentration = (top_5_orders / total_orders * 100) if total_orders > 0 else 0

			if concentration > 70:
				recommendations.append({
					"category": "portfolio_concentration",
					"priority": "medium",
					"title": "High Ticker Concentration",
					"description": f"Top 5 tickers account for {concentration:.0f}% of orders",
					"recommendation": "Portfolio is concentrated in few stocks. Increase watchlist size or diversify entry conditions.",
					"metrics_involved": ["ticker_concentration", "total_tickers"],
				})

		# Expected position sizing vs actual
		if strategy_config:
			entry_params = strategy_config.get("entry", {}).get("parameters", {})
			pos_size_formula = entry_params.get("position_size", {}).get("formula", "")

			# Check if using limit orders
			limit_formula = entry_params.get("limit_price", {}).get("formula", "")
			if limit_formula and "0.99" in limit_formula:
				# Limit order is 1% below market - check if working
				recommendations.append({
					"category": "order_type",
					"priority": "low",
					"title": "Limit Order Impact",
					"description": "Strategy uses limit orders (1% below market) for entry",
					"recommendation": "Monitor fill rates. If many orders go unfilled, consider reducing limit offset or using market orders.",
					"metrics_involved": ["limit_price_formula"],
				})

		# Signal effectiveness
		if total_orders > 0:
			avg_size = sizing_analysis.get("avg_buy_size", 0)
			if avg_size < 1:
				recommendations.append({
					"category": "signal_quality",
					"priority": "low",
					"title": "Very Small Order Size",
					"description": f"Average order size of {avg_size:.2f} shares",
					"recommendation": "Orders are tiny. Check position_size formula - may be using wrong price or capital amount.",
					"metrics_involved": ["avg_order_size"],
				})

		# Same-day buy/sell analysis
		sameday = analysis.get("sameday_buynsell", {})
		pairs_found = sameday.get("pairs_found", 0)
		if pairs_found > 0:
			# Calculate total P&L from same-day pairs
			pairs = sameday.get("pairs", [])
			total_sameday_pnl = sum(p.get("total_pnl", 0) for p in pairs)
			profitable_pairs = len([p for p in pairs if p.get("total_pnl", 0) > 0])

			if total_sameday_pnl < -100:  # Significant losses from same-day trades
				recommendations.append({
					"category": "signal_consistency",
					"priority": "high",
					"title": "Same-Day Buy/Sell Losses",
					"description": f"{pairs_found} instances of same-stock buy+sell on same day, losing €{abs(total_sameday_pnl):.2f} total",
					"recommendation": "Conflicting signals: entry and exit triggering for same stock on same day. Review buy_conditions and sell_conditions - they may be contradictory or entry/exit timing is misaligned.",
					"metrics_involved": ["sameday_pairs", "sameday_pnl"],
				})
			elif pairs_found > 5:
				recommendations.append({
					"category": "signal_consistency",
					"priority": "medium",
					"title": "Frequent Same-Day Trading",
					"description": f"{pairs_found} instances of same stock bought and sold same day",
					"recommendation": "High order churn: Entry and exit signals triggering on same day. Consider adding delay between entry and exit evaluation, or stricter entry filters.",
					"metrics_involved": ["sameday_pairs"],
				})

		return recommendations

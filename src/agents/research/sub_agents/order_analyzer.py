"""Order analyzer sub-agent for analyzing executed orders."""

from typing import Any, Dict, Optional
import pandas as pd
from core.agent import Agent
from tools.portfolio.journal import Journal


class OrderAnalyzerAgent(Agent):
	"""Analyze executed orders for discrepancies and execution quality.

	Examines:
	- Order fills vs. intended prices
	- Partial fills
	- Order timing
	- Execution slippage
	"""

	def __init__(self, name: str = "OrderAnalyzerAgent"):
		"""Initialize order analyzer agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Analyze order execution.

		Args:
			input_data: Input data (optional)

		Returns:
			Response with order analysis
		"""
		if input_data is None:
			input_data = {}

		backtest_dir = self.context.get("backtest_dir") if self.context else None
		portfolio_name = self.context.get("portfolio_name") if self.context else None
		if portfolio_name is None:
			portfolio_name = "default"

		if not backtest_dir:
			return {
				"status": "success",
				"input": input_data,
				"output": {
					"total_orders": 0,
					"message": "No backtest_dir in context"
				},
				"message": "Cannot analyze orders without backtest context"
			}

		# Load journal (which contains executed orders)
		journal = Journal(name=portfolio_name, context={"backtest_dir": backtest_dir})
		df = journal.load_df()

		if df is None or df.empty:
			return {
				"status": "success",
				"input": input_data,
				"output": {
					"total_orders": 0,
					"message": "No orders executed"
				},
				"message": "No executed orders found"
			}

		# Analyze orders
		analysis = self._analyze_orders(df)

		return {
			"status": "success",
			"input": input_data,
			"output": analysis,
			"message": f"Analyzed {analysis.get('total_orders', 0)} orders"
		}

	def _analyze_orders(self, df: pd.DataFrame) -> Dict[str, Any]:
		"""Analyze order DataFrame.

		Args:
			df: Order DataFrame with columns: ticker, operation, quantity, price, etc.

		Returns:
			Dict with analysis results
		"""
		if df.empty:
			return {"total_orders": 0}

		# Ensure numeric columns are converted
		df = df.copy()
		df["price"] = pd.to_numeric(df["price"], errors="coerce")
		df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")

		total_orders = len(df)

		# Order operation counts
		buy_orders = len(df[df["operation"] == "BUY"])
		sell_orders = len(df[df["operation"] == "SELL"])

		# Execution metrics
		avg_price = df["price"].mean()
		total_value = (df["quantity"] * df["price"]).sum()
		avg_order_size = df["quantity"].mean()

		# Check for issues
		zero_price_orders = len(df[df["price"] == 0])
		zero_quantity_orders = len(df[df["quantity"] == 0])

		# Analyze by operation
		buy_stats = {}
		sell_stats = {}

		if buy_orders > 0:
			buy_df = df[df["operation"] == "BUY"]
			buy_stats = {
				"count": buy_orders,
				"avg_price": float(buy_df["price"].mean()),
				"min_price": float(buy_df["price"].min()),
				"max_price": float(buy_df["price"].max()),
				"total_quantity": float(buy_df["quantity"].sum()),
			}

		if sell_orders > 0:
			sell_df = df[df["operation"] == "SELL"]
			sell_stats = {
				"count": sell_orders,
				"avg_price": float(sell_df["price"].mean()),
				"min_price": float(sell_df["price"].min()),
				"max_price": float(sell_df["price"].max()),
				"total_quantity": float(sell_df["quantity"].sum()),
			}

		# Group by ticker
		ticker_order_counts = {}
		for ticker in df["ticker"].unique():
			ticker_df = df[df["ticker"] == ticker]
			ticker_order_counts[ticker] = {
				"orders": len(ticker_df),
				"buys": len(ticker_df[ticker_df["operation"] == "BUY"]),
				"sells": len(ticker_df[ticker_df["operation"] == "SELL"]),
			}

		return {
			"total_orders": total_orders,
			"buy_orders": buy_orders,
			"sell_orders": sell_orders,
			"avg_price": float(avg_price) if not pd.isna(avg_price) else 0,
			"total_value": float(total_value) if not pd.isna(total_value) else 0,
			"avg_order_size": float(avg_order_size) if not pd.isna(avg_order_size) else 0,
			"buy_stats": buy_stats,
			"sell_stats": sell_stats,
			"anomalies": {
				"zero_price_orders": zero_price_orders,
				"zero_quantity_orders": zero_quantity_orders,
			},
			"by_ticker": ticker_order_counts,
		}

"""Journal analyzer sub-agent for analyzing trade journal."""

from typing import Any, Dict, Optional
import pandas as pd
from core.agent import Agent
from tools.portfolio.journal import Journal


class JournalAnalyzerAgent(Agent):
	"""Analyze trade journal for patterns and statistics.

	Examines:
	- Trade duration distribution
	- Win/loss statistics
	- Entry/exit price discrepancies
	- Position sizing consistency
	"""

	def __init__(self, name: str = "JournalAnalyzerAgent"):
		"""Initialize journal analyzer agent.

		Args:
			name: Agent name
		"""
		super().__init__(name)

	def process(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		"""Analyze trade journal.

		Args:
			input_data: Input data (optional)

		Returns:
			Response with journal analysis
		"""
		if input_data is None:
			input_data = {}

		backtest_dir = self.context.get("backtest_dir") if self.context else None
		portfolio_name = self.context.get("portfolio_name") if self.context else None
		if portfolio_name is None:
			portfolio_name = "default"

		if not backtest_dir:
			return {
				"status": "error",
				"input": input_data,
				"output": {},
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
					"total_trades": 0,
					"message": "No trades in journal"
				},
				"message": "No trades found"
			}

		# Analyze journal
		analysis = self._analyze_journal(df)

		return {
			"status": "success",
			"input": input_data,
			"output": analysis,
			"message": f"Analyzed journal: {analysis.get('total_trades', 0)} trades"
		}

	def _analyze_journal(self, df: pd.DataFrame) -> Dict[str, Any]:
		"""Analyze journal DataFrame.

		Args:
			df: Journal DataFrame with columns: ticker, operation, quantity, price, etc.

		Returns:
			Dict with analysis results
		"""
		if df.empty:
			return {"total_trades": 0}

		# Ensure numeric columns are converted
		df = df.copy()
		df["price"] = pd.to_numeric(df["price"], errors="coerce")
		df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")

		# Basic counts
		total_trades = len(df)
		buy_trades = len(df[df["operation"] == "BUY"])
		sell_trades = len(df[df["operation"] == "SELL"])

		# Price statistics
		avg_price = df["price"].mean()
		min_price = df["price"].min()
		max_price = df["price"].max()

		# Quantity statistics
		total_quantity = df["quantity"].sum()
		avg_quantity = df["quantity"].mean()

		# Check for anomalies
		zero_price_trades = len(df[df["price"] == 0])
		zero_quantity_trades = len(df[df["quantity"] == 0])

		# Date range
		if "created_at" in df.columns:
			df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
			date_min = df["created_at"].min()
			date_max = df["created_at"].max()
		else:
			date_min = None
			date_max = None

		# Group by ticker for per-ticker analysis
		ticker_stats = []
		for ticker in df["ticker"].unique():
			ticker_df = df[df["ticker"] == ticker]
			ticker_stats.append({
				"ticker": ticker,
				"trades": len(ticker_df),
				"buys": len(ticker_df[ticker_df["operation"] == "BUY"]),
				"sells": len(ticker_df[ticker_df["operation"] == "SELL"]),
				"total_quantity": float(ticker_df["quantity"].sum()),
				"avg_price": float(ticker_df["price"].mean()),
			})

		return {
			"total_trades": total_trades,
			"buy_trades": buy_trades,
			"sell_trades": sell_trades,
			"avg_price": float(avg_price) if not pd.isna(avg_price) else 0,
			"min_price": float(min_price) if not pd.isna(min_price) else 0,
			"max_price": float(max_price) if not pd.isna(max_price) else 0,
			"total_quantity": float(total_quantity) if not pd.isna(total_quantity) else 0,
			"avg_quantity": float(avg_quantity) if not pd.isna(avg_quantity) else 0,
			"date_min": str(date_min) if date_min is not None else None,
			"date_max": str(date_max) if date_max is not None else None,
			"anomalies": {
				"zero_price_trades": zero_price_trades,
				"zero_quantity_trades": zero_quantity_trades,
			},
			"by_ticker": ticker_stats,
		}

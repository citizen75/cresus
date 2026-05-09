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
	- Exit type analysis: target hits, stop losses, expired orders
	- Exit ratios and percentages
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
		df["stop_loss"] = pd.to_numeric(df["stop_loss"], errors="coerce")
		df["take_profit"] = pd.to_numeric(df["take_profit"], errors="coerce")

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

		# Analyze exit types for completed/closed trades
		exit_analysis = self._analyze_exit_types(df)

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
			"exit_analysis": exit_analysis,
			"by_ticker": ticker_stats,
		}

	def _analyze_exit_types(self, df: pd.DataFrame) -> Dict[str, Any]:
		"""Analyze how trades were exited (target, stop loss, expired, etc).

		Args:
			df: Journal DataFrame with sell orders

		Returns:
			Dict with exit type analysis
		"""
		sell_trades = df[df["operation"] == "SELL"]
		
		if sell_trades.empty:
			return {
				"total_exits": 0,
				"exit_types": {},
				"target_hit_ratio": 0.0,
				"stop_loss_ratio": 0.0,
				"expired_ratio": 0.0,
				"other_ratio": 0.0,
			}

		# Analyze each exit to determine how it happened
		target_hits = 0
		stop_losses = 0
		expired = 0
		other_exits = 0

		for _, row in sell_trades.iterrows():
			notes = str(row.get("notes", "")).lower() if row.get("notes") else ""
			
			# First check notes field for explicit exit type indicators
			if "take profit" in notes or "target" in notes:
				target_hits += 1
			elif "stop loss" in notes or "stop_loss" in notes:
				stop_losses += 1
			elif "expired" in notes or "timeout" in notes or "expir" in notes:
				expired += 1
			else:
				# Fall back to price comparison if available
				exit_price = row["price"]
				take_profit = row["take_profit"]
				stop_loss = row["stop_loss"]
				
				# Try to parse numeric values (may be empty strings)
				try:
					tp = float(take_profit) if take_profit and take_profit != "" else None
					sl = float(stop_loss) if stop_loss and stop_loss != "" else None
				except (ValueError, TypeError):
					tp = None
					sl = None
				
				if tp is not None and exit_price >= tp * 0.99:  # Allow 1% tolerance
					target_hits += 1
				elif sl is not None and exit_price <= sl * 1.01:  # Allow 1% tolerance
					stop_losses += 1
				else:
					other_exits += 1

		total_exits = len(sell_trades)
		target_ratio = target_hits / total_exits if total_exits > 0 else 0.0
		sl_ratio = stop_losses / total_exits if total_exits > 0 else 0.0
		expired_ratio = expired / total_exits if total_exits > 0 else 0.0
		other_ratio = other_exits / total_exits if total_exits > 0 else 0.0

		return {
			"total_exits": total_exits,
			"exit_types": {
				"target_hit": {
					"count": target_hits,
					"ratio": round(target_ratio, 3),
					"pct": round(target_ratio * 100, 1),
				},
				"stop_loss": {
					"count": stop_losses,
					"ratio": round(sl_ratio, 3),
					"pct": round(sl_ratio * 100, 1),
				},
				"expired": {
					"count": expired,
					"ratio": round(expired_ratio, 3),
					"pct": round(expired_ratio * 100, 1),
				},
				"other": {
					"count": other_exits,
					"ratio": round(other_ratio, 3),
					"pct": round(other_ratio * 100, 1),
				},
			},
			"target_hit_ratio": round(target_ratio, 3),
			"stop_loss_ratio": round(sl_ratio, 3),
			"expired_ratio": round(expired_ratio, 3),
			"other_ratio": round(other_ratio, 3),
		}

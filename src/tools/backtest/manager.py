"""Backtest management and retrieval."""

import json
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
from utils.env import get_db_root


class BacktestManager:
	"""Manage backtest discovery, retrieval, and analysis."""

	def __init__(self):
		"""Initialize BacktestManager."""
		self.db_root = get_db_root()
		self.backtests_dir = self.db_root / "backtests"

	def list_backtests(self, strategy_name: Optional[str] = None) -> List[Dict[str, Any]]:
		"""List all backtests, optionally filtered by strategy.

		Args:
			strategy_name: Optional strategy to filter by

		Returns:
			List of backtest summaries, newest first
		"""
		backtests = []

		if not self.backtests_dir.exists():
			return backtests

		# Determine directories to scan
		if strategy_name:
			strategy_dirs = [self.backtests_dir / strategy_name]
		else:
			strategy_dirs = [d for d in self.backtests_dir.iterdir() if d.is_dir()]

		for strategy_dir in strategy_dirs:
			if not strategy_dir.exists():
				continue

			strategy = strategy_dir.name
			for run_dir in sorted(strategy_dir.iterdir(), reverse=True):
				if not run_dir.is_dir():
					continue

				backtest_id = run_dir.name
				summary = self._load_backtest_summary(strategy, backtest_id)
				if summary:
					backtests.append(summary)

		# Sort by created_at descending (newest first)
		backtests.sort(key=lambda x: x.get("created_at", ""), reverse=True)
		return backtests

	def get_backtest(self, strategy_name: str, backtest_id: str) -> Dict[str, Any]:
		"""Get full details of a single backtest.

		Args:
			strategy_name: Strategy name
			backtest_id: Backtest ID (timestamp_uuid)

		Returns:
			Detailed backtest data with metrics, positions, equity curve, trades
		"""
		backtest_dir = self.backtests_dir / strategy_name / backtest_id

		if not backtest_dir.exists():
			return {"status": "error", "message": "Backtest not found"}

		result = self._load_backtest_summary(strategy_name, backtest_id)
		if not result:
			return {"status": "error", "message": "Failed to load backtest"}

		# Load portfolios.json for metrics
		portfolios_file = backtest_dir / "portfolios.json"
		if portfolios_file.exists():
			portfolios = self._load_portfolios_json(portfolios_file)
			if portfolios and "portfolios" in portfolios:
				portfolio_data = next(iter(portfolios["portfolios"].values()), {})
				result["portfolio_metrics"] = portfolio_data.get("metrics", {})
				result["positions"] = portfolio_data.get("positions", {}).get("data", [])

		# Compute equity curve from journal
		equity_curve = self._compute_equity_curve(strategy_name, backtest_id)
		if equity_curve:
			result["equity_curve"] = equity_curve

		# Load trades from journal CSV
		trades = self._load_journal_trades(strategy_name, backtest_id)
		if trades is not None:
			result["trades"] = trades

		return {"status": "success", "data": result}

	def get_backtests_for_compare(
		self, items: List[Dict[str, str]]
	) -> Dict[str, Any]:
		"""Get data for comparing multiple backtests.

		Args:
			items: List of {strategy, backtest_id}

		Returns:
			List of comparison data
		"""
		compare_data = []

		for item in items:
			strategy = item.get("strategy", "")
			backtest_id = item.get("backtest_id", "")

			result = self.get_backtest(strategy, backtest_id)
			if result.get("status") == "success":
				data = result.get("data", {})
				compare_data.append(
					{
						"backtest_id": backtest_id,
						"strategy_name": strategy,
						"created_at": data.get("created_at"),
						"portfolio_metrics": data.get("portfolio_metrics", {}),
						"equity_curve": data.get("equity_curve", []),
					}
				)

		return {"status": "success", "data": compare_data}

	def delete_backtest(self, strategy_name: str, backtest_id: str) -> Dict[str, Any]:
		"""Delete a backtest directory.

		Args:
			strategy_name: Strategy name
			backtest_id: Backtest ID

		Returns:
			Status dict
		"""
		backtest_dir = self.backtests_dir / strategy_name / backtest_id

		if not backtest_dir.exists():
			return {"status": "error", "message": "Backtest not found"}

		try:
			shutil.rmtree(backtest_dir)
			return {"status": "success", "message": f"Deleted backtest {backtest_id}"}
		except Exception as e:
			return {"status": "error", "message": str(e)}

	def _load_backtest_summary(self, strategy_name: str, backtest_id: str) -> Optional[Dict[str, Any]]:
		"""Load summary data for a single backtest."""
		backtest_dir = self.backtests_dir / strategy_name / backtest_id

		if not backtest_dir.exists():
			return None

		# Parse created_at from backtest_id
		created_at = self._parse_created_at(backtest_id)

		# Load portfolios.json
		portfolios_file = backtest_dir / "portfolios.json"
		if not portfolios_file.exists():
			return None

		portfolios = self._load_portfolios_json(portfolios_file)
		if not portfolios or "portfolios" not in portfolios:
			return None

		# Extract metrics from first portfolio
		portfolio_data = next(iter(portfolios["portfolios"].values()), {})
		metrics = portfolio_data.get("metrics", {})

		return {
			"backtest_id": backtest_id,
			"strategy_name": strategy_name,
			"created_at": created_at,
			"total_return_pct": metrics.get("total_return_pct", 0),
			"max_drawdown_pct": metrics.get("max_drawdown_pct", 0),
			"sharpe_ratio": metrics.get("sharpe_ratio", 0),
			"total_trades": metrics.get("total_trades", 0),
			"win_rate_pct": metrics.get("win_rate_pct", 0),
		}

	def _parse_created_at(self, backtest_id: str) -> str:
		"""Parse ISO datetime from backtest_id (YYYYMMDD_HHMMSS_uuid).

		Args:
			backtest_id: Backtest ID string

		Returns:
			ISO datetime string
		"""
		try:
			parts = backtest_id.split("_")
			if len(parts) >= 2:
				date_part = parts[0]  # YYYYMMDD
				time_part = parts[1]  # HHMMSS

				year = int(date_part[:4])
				month = int(date_part[4:6])
				day = int(date_part[6:8])

				hour = int(time_part[:2])
				minute = int(time_part[2:4])
				second = int(time_part[4:6])

				dt = datetime(year, month, day, hour, minute, second)
				return dt.isoformat()
		except Exception:
			pass

		return ""

	def _load_portfolios_json(self, filepath: Path) -> Optional[Dict[str, Any]]:
		"""Load portfolios.json, handling NaN values.

		Args:
			filepath: Path to portfolios.json

		Returns:
			Parsed JSON dict, or None if error
		"""
		try:
			with open(filepath, "r") as f:
				text = f.read()

			# Replace NaN with null for JSON compatibility
			text = re.sub(r"\bNaN\b", "null", text)
			return json.loads(text)
		except Exception:
			return None

	def _compute_equity_curve(self, strategy_name: str, backtest_id: str) -> Optional[List[Dict[str, Any]]]:
		"""Compute equity curve from journal CSV.

		Args:
			strategy_name: Strategy name
			backtest_id: Backtest ID

		Returns:
			List of {date, value} dicts
		"""
		backtest_dir = self.backtests_dir / strategy_name / backtest_id

		# Find journal CSV
		portfolios_dir = backtest_dir / "portfolios"
		if not portfolios_dir.exists():
			return None

		journal_files = list(portfolios_dir.glob("*_journal.csv"))
		if not journal_files:
			return None

		journal_file = journal_files[0]

		try:
			df = pd.read_csv(journal_file)

			# Parse dates
			df["created_at"] = pd.to_datetime(df["created_at"])

			# Group by date and compute cumulative PnL
			daily = df.groupby(df["created_at"].dt.date).agg(
				{
					"amount": "sum",  # Net amount (positive = profit, negative = loss)
				}
			).reset_index()

			daily.rename(columns={"created_at": "date"}, inplace=True)

			# Compute cumulative value (starting from 100000)
			initial_capital = 100000.0
			daily["cumulative_pnl"] = daily["amount"].cumsum()
			daily["value"] = initial_capital + daily["cumulative_pnl"]

			# Return as list of dicts
			result = []
			for _, row in daily.iterrows():
				result.append(
					{
						"date": str(row["date"]),
						"value": float(row["value"]),
					}
				)

			return result

		except Exception:
			return None

	def _load_journal_trades(
		self, strategy_name: str, backtest_id: str
	) -> Optional[List[Dict[str, Any]]]:
		"""Load trades from journal CSV.

		Args:
			strategy_name: Strategy name
			backtest_id: Backtest ID

		Returns:
			List of trade dicts
		"""
		backtest_dir = self.backtests_dir / strategy_name / backtest_id

		# Find journal CSV
		portfolios_dir = backtest_dir / "portfolios"
		if not portfolios_dir.exists():
			return None

		journal_files = list(portfolios_dir.glob("*_journal.csv"))
		if not journal_files:
			return None

		journal_file = journal_files[0]

		try:
			df = pd.read_csv(journal_file)
			# Convert to list of dicts
			trades = df.to_dict(orient="records")
			return trades
		except Exception:
			return None

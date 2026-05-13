"""Backtest management and retrieval."""

import json
import re
import shutil
import uuid
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Any, Dict, List, Optional
import pandas as pd
from utils.env import get_db_root

logger = logging.getLogger(__name__)


class BacktestManager:
	"""Manage backtest discovery, retrieval, and analysis."""

	def __init__(self):
		"""Initialize BacktestManager."""
		self.db_root = get_db_root()
		self.backtests_dir = self.db_root / "backtests"
		self.logger = logger

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

		# Load full metrics from metrics.json, or calculate from portfolio history
		metrics_file = backtest_dir / "metrics.json"
		if metrics_file.exists():
			try:
				with open(metrics_file) as f:
					text = f.read()
					# Replace NaN with null for JSON compatibility
					text = re.sub(r"\bNaN\b", "null", text)
					metrics = json.loads(text)
					result["portfolio_metrics"] = metrics
					# Also merge top-level metrics for backwards compatibility
					result.update(metrics)
			except Exception as e:
				self.logger.warning(f"Failed to load metrics from {metrics_file}: {e}")
		else:
			# For older backtests without metrics.json, calculate from portfolio history
			history_result = self.get_portfolio_history(strategy_name, backtest_id)
			if history_result.get("status") == "success":
				history = history_result.get("history", [])
				if history:
					final_point = history[-1]
					metrics = {
						"total_return_pct": final_point.get("return_pct", 0),
						"max_drawdown_pct": min(h.get("drawdown_pct", 0) for h in history),
						"sharpe_ratio": 0,  # Would need volatility calculation
						"sortino_ratio": 0,
						"calmar_ratio": 0,
						"total_trades": result.get("total_trades", 0),
						"win_rate_pct": result.get("win_rate_pct", 0),
						"profit_factor": 0,
					}
					result["portfolio_metrics"] = metrics
					result.update(metrics)

		# Load portfolios.json for positions and portfolio data
		portfolios_file = backtest_dir / "portfolios.json"
		if portfolios_file.exists():
			portfolios = self._load_portfolios_json(portfolios_file)
			if portfolios and "portfolios" in portfolios:
				portfolio_data = next(iter(portfolios["portfolios"].values()), {})
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

	def initialize_backtest(
		self,
		strategy_name: str,
		start_date: date,
		end_date: date,
		lookback_days: int = 365,
		backtest_id: str = None
	) -> Dict[str, Any]:
		"""Initialize a new backtest run.

		Generates backtest ID (if not provided), creates directory structure, and returns backtest context.

		Args:
			strategy_name: Strategy name
			start_date: Backtest start date
			end_date: Backtest end date
			lookback_days: Lookback period in days
			backtest_id: Optional pre-generated backtest ID. If not provided, generates one.

		Returns:
			Dict with status, backtest_id, backtest_dir, and context dict (or error)
		"""
		try:
			# Use provided backtest_id or generate a new one
			if not backtest_id:
				backtest_id = f"{date.today().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

			# Create directory
			dir_result = self.create_backtest_dir(strategy_name, backtest_id)
			if dir_result.get("status") != "success":
				return {
					"status": "error",
					"message": f"Failed to create backtest directory: {dir_result.get('message')}",
				}

			backtest_dir = dir_result.get("backtest_dir")

			# Initialize backtest context
			backtest = {
				"strategy_name": strategy_name,
				"backtest_id": backtest_id,
				"backtest_dir": backtest_dir,
				"start_date": start_date.isoformat(),
				"end_date": end_date.isoformat(),
				"lookback_days": lookback_days,
				"daily_results": [],
				"metrics": {},
			}

			return {
				"status": "success",
				"backtest_id": backtest_id,
				"backtest_dir": backtest_dir,
				"backtest": backtest,
			}
		except Exception as e:
			return {
				"status": "error",
				"message": f"Failed to initialize backtest: {str(e)}",
			}

	def create_backtest_dir(self, strategy_name: str, backtest_id: str) -> Dict[str, Any]:
		"""Create backtest directory structure.

		Args:
			strategy_name: Strategy name
			backtest_id: Backtest ID

		Returns:
			Dict with status and backtest_dir path
		"""
		try:
			backtest_dir = self.backtests_dir / strategy_name / backtest_id
			backtest_dir.mkdir(parents=True, exist_ok=True)

			# Create subdirectories
			(backtest_dir / "portfolios").mkdir(exist_ok=True)
			(backtest_dir / "orders").mkdir(exist_ok=True)
			(backtest_dir / "watchlist").mkdir(exist_ok=True)

			return {
				"status": "success",
				"backtest_dir": str(backtest_dir),
				"backtest_id": backtest_id,
			}
		except Exception as e:
			return {"status": "error", "message": str(e)}

	def save_strategy(self, strategy_name: str, backtest_id: str, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
		"""Save strategy YAML to backtest directory.

		Args:
			strategy_name: Strategy name
			backtest_id: Backtest ID
			strategy_data: Strategy configuration dict

		Returns:
			Status dict
		"""
		try:
			import yaml

			backtest_dir = self.backtests_dir / strategy_name / backtest_id
			strategy_file = backtest_dir / f"{strategy_name}.yml"

			with open(strategy_file, "w") as f:
				yaml.dump(strategy_data, f, default_flow_style=False)

			return {
				"status": "success",
				"file": str(strategy_file),
				"size": strategy_file.stat().st_size,
			}
		except Exception as e:
			return {"status": "error", "message": str(e)}

	def save_metrics(self, strategy_name: str, backtest_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
		"""Save backtest metrics to JSON file.

		Args:
			strategy_name: Strategy name
			backtest_id: Backtest ID
			metrics: Metrics dict

		Returns:
			Status dict
		"""
		try:
			backtest_dir = self.backtests_dir / strategy_name / backtest_id
			metrics_file = backtest_dir / "metrics.json"

			# Handle NaN values
			metrics_clean = json.loads(
				re.sub(r"\bNaN\b", "null", json.dumps(metrics, default=str))
			)

			with open(metrics_file, "w") as f:
				json.dump(metrics_clean, f, indent=2)

			return {
				"status": "success",
				"file": str(metrics_file),
				"metrics_count": len(metrics),
			}
		except Exception as e:
			return {"status": "error", "message": str(e)}

	def get_metrics(self, strategy_name: str, backtest_id: str) -> Dict[str, Any]:
		"""Load metrics from backtest.

		Args:
			strategy_name: Strategy name
			backtest_id: Backtest ID

		Returns:
			Metrics dict or empty dict if not found
		"""
		backtest_dir = self.backtests_dir / strategy_name / backtest_id
		metrics_file = backtest_dir / "metrics.json"

		if not metrics_file.exists():
			return {}

		try:
			with open(metrics_file, "r") as f:
				text = f.read()
				# Replace NaN with null for JSON compatibility
				text = re.sub(r"\bNaN\b", "null", text)
				return json.loads(text)
		except Exception:
			return {}

	def _load_backtest_summary(self, strategy_name: str, backtest_id: str) -> Optional[Dict[str, Any]]:
		"""Load summary data for a single backtest."""
		backtest_dir = self.backtests_dir / strategy_name / backtest_id

		if not backtest_dir.exists():
			return None

		# Parse created_at from backtest_id
		created_at = self._parse_created_at(backtest_id)

		# Try to load metrics from metrics.json first (new format)
		metrics_file = backtest_dir / "metrics.json"
		if metrics_file.exists():
			try:
				with open(metrics_file) as f:
					text = f.read()
					text = re.sub(r"\bNaN\b", "null", text)
					metrics = json.loads(text)
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
			except Exception as e:
				logger.warning(f"Failed to load metrics.json for {backtest_id}: {e}")

		# Fallback to portfolios.json (old format)
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
		"""Compute equity curve from journal CSV with drawdown.

		Args:
			strategy_name: Strategy name
			backtest_id: Backtest ID

		Returns:
			List of {date, value, drawdown_pct} dicts
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

			# Compute drawdown (running maximum minus current value)
			daily["running_max"] = daily["value"].expanding().max()
			daily["drawdown_pct"] = ((daily["value"] - daily["running_max"]) / daily["running_max"] * 100)

			# Return as list of dicts
			result = []
			for _, row in daily.iterrows():
				result.append(
					{
						"date": str(row["date"]),
						"value": float(row["value"]),
						"drawdown_pct": float(row["drawdown_pct"]),
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

	def get_portfolio_history(self, strategy_name: str, backtest_id: str) -> Dict[str, Any]:
		"""Get portfolio history with evolving metrics.

		Args:
			strategy_name: Strategy name
			backtest_id: Backtest ID

		Returns:
			Historical data with daily equity values, returns, and drawdown
		"""
		backtest_dir = self.backtests_dir / strategy_name / backtest_id

		if not backtest_dir.exists():
			return {"status": "error", "message": "Backtest not found"}

		# Load equity curve (already calculated by BacktestAgent)
		equity_curve = self._compute_equity_curve(strategy_name, backtest_id)
		if not equity_curve:
			return {"status": "error", "message": "No equity curve data available"}

		# Calculate metrics at each point in time
		initial_capital = 100000.0
		history = []
		peak_value = initial_capital
		max_drawdown = 0.0

		for i, point in enumerate(equity_curve):
			current_value = point["value"]

			# Track peak (running maximum)
			if current_value > peak_value:
				peak_value = current_value

			# Calculate cumulative return
			cumulative_return = ((current_value - initial_capital) / initial_capital) * 100

			# Calculate drawdown from peak (will be negative when below peak)
			drawdown = ((current_value - peak_value) / peak_value) * 100 if peak_value > 0 else 0

			# Track maximum drawdown (most negative value)
			if drawdown < max_drawdown:
				max_drawdown = drawdown

			history.append({
				"date": point["date"],
				"value": current_value,
				"return_pct": cumulative_return,
				"drawdown_pct": drawdown,
			})

		return {
			"status": "success",
			"strategy_name": strategy_name,
			"backtest_id": backtest_id,
			"history": history,
			"initial_capital": initial_capital,
			"max_drawdown_pct": max_drawdown,
		}

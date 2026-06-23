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
from tools.data.core import DataHistory

logger = logging.getLogger(__name__)


class BacktestManager:
	"""Manage backtest discovery, retrieval, and analysis."""

	def __init__(self):
		"""Initialize BacktestManager."""
		self.db_root = get_db_root()
		self.backtests_dir = self.db_root / "backtests"
		self.logger = logger

	# ------------------------------------------------------------------
	# Path safety
	# ------------------------------------------------------------------

	def _resolve_strategy_dir(self, strategy_name: str) -> Optional[Path]:
		"""Resolve a strategy's backtests directory, refusing to escape backtests_dir.

		strategy_name ultimately comes from API path parameters, so this guards
		against path traversal (e.g. '../../etc') resolving outside the intended
		backtests directory.
		"""
		try:
			base = self.backtests_dir.resolve()
			candidate = (self.backtests_dir / strategy_name).resolve()
			candidate.relative_to(base)
			return candidate
		except (ValueError, OSError):
			self.logger.warning(f"Rejected unsafe strategy path: strategy={strategy_name!r}")
			return None

	def _resolve_backtest_dir(self, strategy_name: str, backtest_id: str) -> Optional[Path]:
		"""Resolve the on-disk directory for a backtest, refusing to escape backtests_dir."""
		strategy_dir = self._resolve_strategy_dir(strategy_name)
		if strategy_dir is None:
			return None
		try:
			base = self.backtests_dir.resolve()
			candidate = (strategy_dir / backtest_id).resolve()
			candidate.relative_to(base)
			return candidate
		except (ValueError, OSError):
			self.logger.warning(
				f"Rejected unsafe backtest path: strategy={strategy_name!r} backtest_id={backtest_id!r}"
			)
			return None

	# ------------------------------------------------------------------
	# Shared helpers
	# ------------------------------------------------------------------

	def _read_json_safe(self, filepath: Path) -> Optional[Dict[str, Any]]:
		"""Read a JSON file, tolerating bare NaN tokens emitted by older writers.

		Returns None if the file doesn't exist or can't be parsed.
		"""
		if not filepath.exists():
			return None
		try:
			text = filepath.read_text()
			text = re.sub(r"\bNaN\b", "null", text)
			return json.loads(text)
		except Exception as e:
			self.logger.debug(f"Failed to read {filepath}: {e}")
			return None

	def _get_initial_capital(self, metrics: Optional[Dict[str, Any]]) -> float:
		"""Single source of truth for the default starting-capital fallback."""
		if metrics:
			value = metrics.get("start_value")
			if value is not None:
				try:
					return float(value)
				except (TypeError, ValueError):
					pass
		return 10000.0

	def _find_journal_file(self, backtest_dir: Path) -> Optional[Path]:
		"""Find the portfolio journal CSV for a backtest.

		Supports all formats produced over time:
		  1. portfolios/journal.csv
		  2. portfolios/*_journal.csv (legacy flat naming)
		  3. portfolios/<portfolio_name>/journal.csv (current format)
		"""
		portfolios_dir = backtest_dir / "portfolios"
		if not portfolios_dir.exists():
			return None

		candidates = list(portfolios_dir.glob("journal.csv"))
		if not candidates:
			candidates = list(portfolios_dir.glob("*_journal.csv"))
		if not candidates:
			candidates = list(portfolios_dir.glob("*/journal.csv"))
		if not candidates:
			return None

		if len(candidates) > 1:
			self.logger.warning(
				f"Multiple journal files found under {portfolios_dir}, using "
				f"{candidates[0].name} (ignoring {len(candidates) - 1} other(s)) - "
				f"multi-portfolio backtests aren't fully supported yet"
			)
		return candidates[0]

	def _apply_peak_drawdown(
		self, points: List[Dict[str, Any]], initial_value: float
	) -> List[Dict[str, Any]]:
		"""Annotate {date, value} points with a running-peak drawdown_pct (<= 0).

		Single canonical implementation shared by _compute_equity_curve, the
		final-point correction in get_backtest, and get_portfolio_history, so the
		three don't drift out of sync with slightly different peak-tracking logic.
		"""
		peak = initial_value
		annotated = []
		for point in points:
			value = point["value"]
			if value > peak:
				peak = value
			drawdown_pct = ((value - peak) / peak * 100) if peak > 0 else 0.0
			annotated.append({**point, "drawdown_pct": float(drawdown_pct)})
		return annotated

	def _reconcile_curve_with_metrics(
		self, equity_curve: List[Dict[str, Any]], metrics: Dict[str, Any]
	) -> List[Dict[str, Any]]:
		"""Force the curve's final point to agree with metrics.json's authoritative
		end_value, so any consumer of the curve always matches the Key Metrics panel.

		Shared by get_backtest and get_portfolio_history - both expose an equity
		curve, and previously only get_backtest applied this correction, so the two
		endpoints could silently disagree once a backtest finished.
		"""
		if not equity_curve:
			return equity_curve

		end_value = metrics.get("end_value")
		end_date = metrics.get("end_date")
		if not end_value or not end_date:
			return equity_curve

		# Parse end_date (may be "2025-12-15 00:00:00" format)
		end_date_str = end_date.split()[0] if isinstance(end_date, str) else str(end_date)
		last_point_date = equity_curve[-1].get("date")

		if last_point_date and last_point_date < end_date_str:
			# Last trading day is before the requested end_date - append the
			# authoritative final value as its own point
			equity_curve.append({"date": end_date_str, "value": float(end_value)})
		else:
			# Last trading day is on or after end_date (e.g. an order placed on the
			# final day settles on the next trading day, which can spill into the
			# following year) - overwrite that last point with the authoritative
			# end_value so the chart always agrees with the Key Metrics panel.
			equity_curve[-1]["value"] = float(end_value)

		# Re-derive drawdown_pct for the (possibly appended/overwritten) curve
		initial_capital = self._get_initial_capital(metrics)
		return self._apply_peak_drawdown(
			[{"date": p["date"], "value": p["value"]} for p in equity_curve],
			initial_capital,
		)

	# ------------------------------------------------------------------
	# Listing / retrieval
	# ------------------------------------------------------------------

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
			resolved = self._resolve_strategy_dir(strategy_name)
			strategy_dirs = [resolved] if resolved else []
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
		backtest_dir = self._resolve_backtest_dir(strategy_name, backtest_id)
		if backtest_dir is None or not backtest_dir.exists():
			return {"status": "error", "message": "Backtest not found"}

		result = self._load_backtest_summary(strategy_name, backtest_id)
		if not result:
			# Backtest is running in memory - return minimal response indicating it's processing
			return {
				"status": "success",
				"backtest_id": backtest_id,
				"strategy_name": strategy_name,
				"data": {},
				"message": "Backtest in progress - results not finalized yet"
			}

		# Load full metrics from metrics.json, or calculate from portfolio history
		metrics_data = self._read_json_safe(backtest_dir / "metrics.json")
		if metrics_data:
			result["portfolio_metrics"] = metrics_data
			# Also merge top-level metrics for backwards compatibility, but never let
			# metrics.json clobber this record's own identity fields if a future
			# metrics schema happens to add a colliding key name.
			identity = {k: result.get(k) for k in ("backtest_id", "strategy_name", "created_at")}
			result.update(metrics_data)
			result.update(identity)
		else:
			# For older backtests without metrics.json, calculate from portfolio history
			history_result = self.get_portfolio_history(strategy_name, backtest_id)
			if history_result.get("status") == "success":
				history = history_result.get("history", [])
				if history:
					final_point = history[-1]
					most_negative_drawdown = min(
						(h.get("drawdown_pct", 0) for h in history), default=0
					)
					metrics_data = {
						"total_return_pct": final_point.get("return_pct", 0),
						# drawdown_pct on history points is <= 0 (running-peak convention);
						# max_drawdown_pct is reported elsewhere as a positive magnitude.
						"max_drawdown_pct": abs(most_negative_drawdown),
						"sharpe_ratio": 0,  # Would need volatility calculation
						"sortino_ratio": 0,
						"calmar_ratio": 0,
						"total_trades": result.get("total_trades", 0),
						"win_rate_pct": result.get("win_rate_pct", 0),
						"profit_factor": 0,
					}
					result["portfolio_metrics"] = metrics_data
					result.update(metrics_data)

		# Currently-open positions, computed by replaying the journal. portfolios.json's
		# current schema doesn't carry a per-position breakdown.
		result["positions"] = self._compute_open_positions(strategy_name, backtest_id)

		# Compute equity curve from journal, daily mark-to-market
		metrics_for_curve = result.get("portfolio_metrics") or {}
		equity_curve = self._compute_equity_curve(strategy_name, backtest_id, metrics=metrics_for_curve)
		if equity_curve:
			result["equity_curve"] = self._reconcile_curve_with_metrics(equity_curve, metrics_for_curve)

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
		backtest_dir = self._resolve_backtest_dir(strategy_name, backtest_id)
		if backtest_dir is None:
			return {"status": "error", "message": "Invalid strategy_name or backtest_id"}

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
				backtest_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

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
		backtest_dir = self._resolve_backtest_dir(strategy_name, backtest_id)
		if backtest_dir is None:
			return {"status": "error", "message": "Invalid strategy_name or backtest_id"}

		try:
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
		backtest_dir = self._resolve_backtest_dir(strategy_name, backtest_id)
		if backtest_dir is None:
			return {"status": "error", "message": "Invalid strategy_name or backtest_id"}

		try:
			import yaml

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
		backtest_dir = self._resolve_backtest_dir(strategy_name, backtest_id)
		if backtest_dir is None:
			return {"status": "error", "message": "Invalid strategy_name or backtest_id"}

		try:
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
		backtest_dir = self._resolve_backtest_dir(strategy_name, backtest_id)
		if backtest_dir is None:
			return {}

		return self._read_json_safe(backtest_dir / "metrics.json") or {}

	def _load_backtest_summary(self, strategy_name: str, backtest_id: str) -> Optional[Dict[str, Any]]:
		"""Load summary data for a single backtest."""
		backtest_dir = self._resolve_backtest_dir(strategy_name, backtest_id)
		if backtest_dir is None or not backtest_dir.exists():
			return None

		# Parse created_at from backtest_id
		created_at = self._parse_created_at(backtest_id)

		# Try to load metrics from metrics.json first (new format)
		metrics = self._read_json_safe(backtest_dir / "metrics.json")
		if metrics:
			return {
				"backtest_id": backtest_id,
				"strategy_name": strategy_name,
				"created_at": created_at,
				"start_date": metrics.get("start_date"),
				"end_date": metrics.get("end_date"),
				"total_return_pct": metrics.get("total_return_pct", 0),
				"max_drawdown_pct": metrics.get("max_drawdown_pct", 0),
				"sharpe_ratio": metrics.get("sharpe_ratio", 0),
				"total_trades": metrics.get("total_trades", 0),
				"win_rate_pct": metrics.get("win_rate_pct", 0),
			}

		# Fallback to portfolios.json (old format). Current portfolios.json schema is
		# a flat cash/positions-value summary with no per-backtest metrics breakdown,
		# so this is only meaningful for genuinely old backtests that predate
		# metrics.json and still carry a "metrics" key under their portfolio entry.
		portfolios_file = backtest_dir / "portfolios.json"
		if not portfolios_file.exists():
			return None

		portfolios = self._read_json_safe(portfolios_file)
		if not portfolios or "portfolios" not in portfolios:
			return None

		portfolio_data = next(iter(portfolios["portfolios"].values()), {})
		legacy_metrics = portfolio_data.get("metrics")
		if not legacy_metrics:
			# No metrics.json and no legacy metrics breakdown - nothing authoritative
			# to report, rather than fabricating an all-zero summary.
			return None

		return {
			"backtest_id": backtest_id,
			"strategy_name": strategy_name,
			"created_at": created_at,
			"start_date": portfolios.get("start_date"),
			"end_date": portfolios.get("end_date"),
			"total_return_pct": legacy_metrics.get("total_return_pct", 0),
			"max_drawdown_pct": legacy_metrics.get("max_drawdown_pct", 0),
			"sharpe_ratio": legacy_metrics.get("sharpe_ratio", 0),
			"total_trades": legacy_metrics.get("total_trades", 0),
			"win_rate_pct": legacy_metrics.get("win_rate_pct", 0),
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
		except Exception as e:
			self.logger.debug(f"Failed to parse created_at from backtest_id {backtest_id!r}: {e}")

		return ""

	def _load_portfolios_json(self, filepath: Path) -> Optional[Dict[str, Any]]:
		"""Load portfolios.json, handling NaN values.

		Args:
			filepath: Path to portfolios.json

		Returns:
			Parsed JSON dict, or None if error
		"""
		return self._read_json_safe(filepath)

	# ------------------------------------------------------------------
	# Equity curve / positions
	# ------------------------------------------------------------------

	def _compute_equity_curve(
		self,
		strategy_name: str,
		backtest_id: str,
		metrics: Optional[Dict[str, Any]] = None,
	) -> Optional[List[Dict[str, Any]]]:
		"""Compute a daily, mark-to-market equity curve from the journal CSV.

		Produces one point per trading day in range (not just days a transaction
		happened), valuing open positions at that day's actual close price from the
		local price cache (falling back to cost basis for any ticker without cached
		price history), so the chart reflects real day-to-day P&L drift instead of a
		flat line between trades.

		Args:
			strategy_name: Strategy name
			backtest_id: Backtest ID
			metrics: Already-loaded metrics.json contents, to avoid re-reading the
				file when the caller already has it

		Returns:
			List of {date, value, drawdown_pct} dicts
		"""
		backtest_dir = self._resolve_backtest_dir(strategy_name, backtest_id)
		if backtest_dir is None:
			return None

		if metrics is None:
			metrics = self._read_json_safe(backtest_dir / "metrics.json") or {}
		initial_capital = self._get_initial_capital(metrics)

		journal_file = self._find_journal_file(backtest_dir)
		if journal_file is None:
			return None

		try:
			df = pd.read_csv(journal_file)
			if df.empty:
				return []

			# format="mixed": a settlement/spillover transaction past the configured
			# end_date is written with a plain isoformat() timestamp, while every
			# regular trading-day transaction uses the day-loop's "YYYY-MM-DD HH:MM:SS"
			# format - a strict single-format parse raises on whichever rows don't
			# match the format inferred from the first row.
			df["created_at"] = pd.to_datetime(df["created_at"], format="mixed")
			df["operation"] = df["operation"].astype(str).str.upper()
			df["ticker"] = df["ticker"].astype(str).str.upper()
			df = df.sort_values("created_at")
			df["trade_date"] = df["created_at"].dt.date

			journal_start = df["trade_date"].min()
			journal_end = df["trade_date"].max()

			# Day axis bound: extend through the backtest's configured end_date (a
			# settlement can land a day or two after the last journal entry), so the
			# curve's last point lines up with the authoritative end_value correction
			# applied by _reconcile_curve_with_metrics.
			end_bound = journal_end
			end_date_cfg = metrics.get("end_date")
			if end_date_cfg:
				try:
					end_bound = max(end_bound, pd.to_datetime(end_date_cfg).date())
				except (ValueError, TypeError):
					pass

			# Load cached price history for every traded ticker, building a
			# forward-filled close-price lookup across the full day axis.
			tickers = sorted(t for t in df["ticker"].unique() if t and t != "CASH")
			price_series_by_ticker: Dict[str, pd.Series] = {}
			all_price_dates = set()
			for ticker in tickers:
				# Isolated per-ticker: one missing/corrupt price cache must not blank
				# out the equity curve for the whole backtest (caught broadly since
				# DataHistory can hit anything from a missing file to a parse error).
				try:
					hist = DataHistory(ticker).load_all()
					if hist.empty or "timestamp" not in hist.columns or "close" not in hist.columns:
						continue
					hist = hist.dropna(subset=["close"])
					if hist.empty:
						continue
					hist_dates = pd.to_datetime(hist["timestamp"]).dt.date
					series = pd.Series(hist["close"].to_numpy(), index=hist_dates)
					series = series[~series.index.duplicated(keep="last")].sort_index()
					price_series_by_ticker[ticker] = series
					all_price_dates.update(series.index)
				except Exception as e:
					self.logger.warning(f"Could not load price history for {ticker}, falling back to cost-basis valuation: {e}")

			trading_days = sorted(d for d in all_price_dates if journal_start <= d <= end_bound)
			if not trading_days:
				# No cached price history available for any traded ticker - fall back
				# to transaction days only (cost-basis valuation throughout).
				trading_days = sorted(df["trade_date"].unique())

			price_table = pd.DataFrame(index=pd.Index(trading_days))
			for ticker, series in price_series_by_ticker.items():
				price_table[ticker] = series.reindex(price_table.index).ffill()

			# Vectorized running cash: one groupby instead of re-masking the whole
			# dataframe for every day.
			buys_by_day = df.loc[df["operation"] == "BUY"].groupby("trade_date")["amount"].sum()
			sells_by_day = df.loc[df["operation"] == "SELL"].groupby("trade_date")["amount"].sum()
			cum_buys = buys_by_day.reindex(trading_days, fill_value=0.0).cumsum()
			cum_sells = sells_by_day.reindex(trading_days, fill_value=0.0).cumsum()

			# Walk transactions once (grouped by day, not re-filtered per day) to
			# maintain per-ticker open qty/cost-basis - used as the mark-to-market
			# fallback when a ticker's price history isn't cached locally.
			txns_by_day = {trade_date: group for trade_date, group in df.groupby("trade_date")}
			positions: Dict[str, Dict[str, float]] = {}
			daily_equity = []

			for i, day in enumerate(trading_days):
				day_txns = txns_by_day.get(day)
				if day_txns is not None:
					for _, txn in day_txns.iterrows():
						ticker = txn["ticker"]
						qty = float(txn["quantity"])
						amount = float(txn["amount"])
						if txn["operation"] == "BUY":
							pos = positions.setdefault(ticker, {"qty": 0.0, "cost": 0.0})
							pos["qty"] += qty
							pos["cost"] += amount
						elif txn["operation"] == "SELL":
							pos = positions.get(ticker)
							if pos and pos["qty"] > 0:
								avg_cost = pos["cost"] / pos["qty"]
								pos["qty"] -= qty
								pos["cost"] -= qty * avg_cost
								if pos["qty"] <= 0:
									pos["qty"] = 0.0
									pos["cost"] = 0.0

				cash = initial_capital - cum_buys.iloc[i] + cum_sells.iloc[i]

				position_value = 0.0
				for ticker, pos in positions.items():
					if pos["qty"] <= 0:
						continue
					price = None
					if ticker in price_table.columns:
						cell = price_table.at[day, ticker]
						if pd.notna(cell):
							price = float(cell)
					position_value += pos["qty"] * price if price is not None else pos["cost"]

				daily_equity.append({"date": str(day), "value": float(cash + position_value)})

			return self._apply_peak_drawdown(daily_equity, initial_capital)

		except Exception as e:
			self.logger.warning(f"Error computing equity curve for {strategy_name}/{backtest_id}: {e}")
			return None

	def _compute_open_positions(self, strategy_name: str, backtest_id: str) -> List[Dict[str, Any]]:
		"""Compute currently-open positions by replaying the journal.

		portfolios.json's current schema no longer carries a per-position
		breakdown, so this is derived directly from the transaction log instead.
		"""
		backtest_dir = self._resolve_backtest_dir(strategy_name, backtest_id)
		if backtest_dir is None:
			return []

		journal_file = self._find_journal_file(backtest_dir)
		if journal_file is None:
			return []

		try:
			df = pd.read_csv(journal_file)
			if df.empty:
				return []

			df["operation"] = df["operation"].astype(str).str.upper()
			df["ticker"] = df["ticker"].astype(str).str.upper()
			# format="mixed": a settlement/spillover transaction past the configured
			# end_date is written with a plain isoformat() timestamp, while every
			# regular trading-day transaction uses the day-loop's "YYYY-MM-DD HH:MM:SS"
			# format - a strict single-format parse raises on whichever rows don't
			# match the format inferred from the first row.
			df["created_at"] = pd.to_datetime(df["created_at"], format="mixed")
			df = df.sort_values("created_at")

			positions: Dict[str, Dict[str, float]] = {}
			for _, txn in df.iterrows():
				ticker = txn["ticker"]
				qty = float(txn["quantity"])
				amount = float(txn["amount"])
				if txn["operation"] == "BUY":
					pos = positions.setdefault(ticker, {"qty": 0.0, "cost": 0.0})
					pos["qty"] += qty
					pos["cost"] += amount
				elif txn["operation"] == "SELL":
					pos = positions.get(ticker)
					if pos and pos["qty"] > 0:
						avg_cost = pos["cost"] / pos["qty"]
						pos["qty"] -= qty
						pos["cost"] -= qty * avg_cost
						if pos["qty"] <= 0:
							pos["qty"] = 0.0
							pos["cost"] = 0.0

			open_positions = []
			for ticker, pos in positions.items():
				if pos["qty"] > 0:
					avg_cost = pos["cost"] / pos["qty"]
					open_positions.append({
						"ticker": ticker,
						"quantity": pos["qty"],
						"avg_cost": round(avg_cost, 4),
						"cost_basis": round(pos["cost"], 2),
					})
			return open_positions

		except Exception as e:
			self.logger.warning(f"Failed to compute open positions for {strategy_name}/{backtest_id}: {e}")
			return []

	def _load_journal_trades(
		self, strategy_name: str, backtest_id: str
	) -> Optional[List[Dict[str, Any]]]:
		"""Load trades from journal CSV.

		Args:
			strategy_name: Strategy name
			backtest_id: Backtest ID

		Returns:
			List of trade dicts with status_at renamed to exit_date
		"""
		backtest_dir = self._resolve_backtest_dir(strategy_name, backtest_id)
		if backtest_dir is None:
			return None

		journal_file = self._find_journal_file(backtest_dir)
		if journal_file is None:
			return None

		try:
			df = pd.read_csv(journal_file)
			# Rename status_at to exit_date for frontend compatibility
			if "status_at" in df.columns:
				df = df.rename(columns={"status_at": "exit_date"})
			# Convert to list of dicts
			return df.to_dict(orient="records")
		except Exception as e:
			self.logger.debug(f"Failed to load journal trades from {journal_file}: {e}")
			return None

	def get_portfolio_history(self, strategy_name: str, backtest_id: str) -> Dict[str, Any]:
		"""Get portfolio history with evolving metrics.

		Args:
			strategy_name: Strategy name
			backtest_id: Backtest ID

		Returns:
			Historical data with daily equity values, returns, and drawdown
		"""
		backtest_dir = self._resolve_backtest_dir(strategy_name, backtest_id)
		if backtest_dir is None or not backtest_dir.exists():
			return {"status": "error", "message": "Backtest not found"}

		metrics = self._read_json_safe(backtest_dir / "metrics.json") or {}
		initial_capital = self._get_initial_capital(metrics)

		# Load equity curve (already calculated by BacktestAgent)
		equity_curve = self._compute_equity_curve(strategy_name, backtest_id, metrics=metrics)
		if not equity_curve:
			# Return empty history while backtest is in progress
			return {
				"status": "success",
				"history": [],
				"max_drawdown_pct": 0,
				"message": "Backtest in progress - data not available yet"
			}

		# Once the backtest has finished (metrics.json exists), agree with the same
		# authoritative end_value get_backtest's equity_curve is corrected against -
		# otherwise this endpoint could report a different final return/drawdown.
		equity_curve = self._reconcile_curve_with_metrics(equity_curve, metrics)

		# _compute_equity_curve / _reconcile_curve_with_metrics already annotated
		# drawdown_pct via the shared running-peak helper - reuse it instead of
		# recomputing peak tracking again.
		history = []
		max_drawdown = 0.0
		for point in equity_curve:
			current_value = point["value"]
			cumulative_return = (
				((current_value - initial_capital) / initial_capital) * 100
				if initial_capital
				else 0.0
			)
			drawdown = point.get("drawdown_pct", 0.0)
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

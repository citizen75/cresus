"""Stage 4 — Portfolio & order management diagnose/fix/optimize/validate
(STRATEGY_IMPROVER v2.0 §4).

Given the locked watchlist/entry/exit, optimizes position sizing, max
positions, and order cadence to maximize risk-adjusted returns at the
portfolio level. Diagnosis works entirely off the trade log plus cached
price history - no fresh data-prep pass is needed since none of these
metrics depend on a formula's indicator columns.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from agents.strategy_tuning.common import cleanup_scratch_backtest, run_scratch_backtest
from tools.data.core import DataHistory
from tools.strategy.optuna_runner import apply_overrides, get_path, run_param_search
from tools.strategy.trade_log import build_trade_records

FEES_PCT_FLAG = 0.20
AVG_POSITIONS_LOW = 2.0
CORRELATION_HIGH = 0.6
CAPITAL_UTILIZATION_LOW = 0.40

POSITION_SIZE_PATH = "entry.parameters.position_size.formula"
MAX_POSITIONS_PATH = "order.parameters.max_positions.formula"
MAX_DAILY_ORDERS_PATH = "order.parameters.max_daily_orders.formula"
INITIAL_CAPITAL_PATH = "backtest.initial_capital"

# Priority order when multiple issues fire at once - anti-pattern #6 (never
# change more than 1 structural element per stage) means fix() acts on only
# the first match.
_FIX_PRIORITY = [
	"fees_high",
	"avg_positions_low",
	"correlation_high",
	"utilization_low",
	"fixed_sizing_high_variance",
]


def compute_fees_pct_of_gross(trade_records: List[Dict[str, Any]], total_fees_paid: Optional[float]) -> Optional[float]:
	"""Fees as % of gross P&L turnover (sum of |realized P&L| across all
	closed trades) - the spec's `fees_pct_of_gross`, target < 15%."""
	if not trade_records or total_fees_paid is None:
		return None
	gross = sum(abs(r["pnl_amount"]) for r in trade_records)
	return (total_fees_paid / gross) if gross else None


def compute_avg_concurrent_positions(trade_records: List[Dict[str, Any]], start_date: str, end_date: str) -> Optional[float]:
	"""Average number of simultaneously open positions across every day in
	the date range - classic interval-overlap counting over each trade's
	[entry_date, exit_date] span."""
	if not trade_records:
		return None
	days = pd.date_range(start_date, end_date, freq="D")
	if len(days) == 0:
		return None
	counts = pd.Series(0, index=days)
	for rec in trade_records:
		entry, exit_ = rec["entry_date"], rec["exit_date"]
		mask = (days >= entry) & (days <= exit_)
		counts.loc[mask] += 1
	return float(counts.mean())


def compute_avg_position_correlation(trade_records: List[Dict[str, Any]]) -> Optional[float]:
	"""Average pairwise daily-return correlation among trades whose holding
	periods overlap - high correlation means concurrently open positions
	aren't actually diversifying risk."""
	if len(trade_records) < 2:
		return None

	tickers = {r["ticker"] for r in trade_records}
	returns: Dict[str, pd.Series] = {}
	for ticker in tickers:
		df = DataHistory(ticker).load_all()
		if df.empty or "close" not in df.columns:
			continue
		df = df.sort_values("timestamp")
		series = df.set_index(pd.to_datetime(df["timestamp"]))["close"].pct_change().dropna()
		returns[ticker] = series

	correlations = []
	for i, a in enumerate(trade_records):
		for b in trade_records[i + 1:]:
			overlap = (a["entry_date"] <= b["exit_date"]) and (b["entry_date"] <= a["exit_date"])
			if not overlap or a["ticker"] == b["ticker"]:
				continue
			ra, rb = returns.get(a["ticker"]), returns.get(b["ticker"])
			if ra is None or rb is None:
				continue
			joined = pd.concat([ra, rb], axis=1, join="inner")
			if len(joined) < 5:
				continue
			corr = joined.iloc[:, 0].corr(joined.iloc[:, 1])
			if pd.notna(corr):
				correlations.append(corr)

	return float(sum(correlations) / len(correlations)) if correlations else None


def compute_capital_utilization(
	trade_records: List[Dict[str, Any]], initial_capital: Optional[float], start_date: str, end_date: str
) -> Optional[float]:
	"""Average fraction of capital invested over the date range - a
	day-weighted approximation (sum of each trade's notional value x its
	holding days, divided by capital x total days) rather than a full
	daily mark-to-market, which would need a per-day equity series this
	stage doesn't otherwise need to load."""
	if not trade_records or not initial_capital:
		return None
	total_days = max((pd.Timestamp(end_date) - pd.Timestamp(start_date)).days, 1)
	invested_days = sum(r["entry_price"] * r["quantity"] * max(r["holding_days"], 1) for r in trade_records)
	return invested_days / (initial_capital * total_days)


def diagnose(
	config: Dict[str, Any],
	portfolio_name: str,
	start_date: str,
	end_date: str,
	portfolio_metrics: Optional[Dict[str, Any]] = None,
	context: Optional[Any] = None,
) -> Dict[str, Any]:
	"""Stage 4.1 - Portfolio Diagnosis (spec §4.1)."""
	trade_records = build_trade_records(portfolio_name, context=context)
	portfolio_metrics = portfolio_metrics or {}
	initial_capital = get_path(config, INITIAL_CAPITAL_PATH)

	fees_pct = compute_fees_pct_of_gross(trade_records, portfolio_metrics.get("total_fees_paid"))
	avg_positions = compute_avg_concurrent_positions(trade_records, start_date, end_date)
	avg_correlation = compute_avg_position_correlation(trade_records)
	capital_utilization = compute_capital_utilization(trade_records, initial_capital, start_date, end_date)

	position_size_formula = get_path(config, POSITION_SIZE_PATH)
	is_vol_adjusted = bool(position_size_formula and "atr" in str(position_size_formula).lower())

	issues: List[str] = []
	if fees_pct is not None and fees_pct > FEES_PCT_FLAG:
		issues.append("fees_high")
	if avg_positions is not None and avg_positions < AVG_POSITIONS_LOW:
		issues.append("avg_positions_low")
	if avg_correlation is not None and avg_correlation > CORRELATION_HIGH:
		issues.append("correlation_high")
	if capital_utilization is not None and capital_utilization < CAPITAL_UTILIZATION_LOW:
		issues.append("utilization_low")
	if not is_vol_adjusted:
		issues.append("fixed_sizing_high_variance")

	if issues:
		summary = f"Issues found: {', '.join(issues)}."
	else:
		summary = "Fees, position count, correlation, and capital utilization are all within target ranges."

	return {
		"fees_pct_of_gross": fees_pct,
		"avg_concurrent_positions": avg_positions,
		"avg_position_correlation": avg_correlation,
		"capital_utilization": capital_utilization,
		"position_sizing_is_vol_adjusted": is_vol_adjusted,
		"trade_count": len(trade_records),
		"issues": issues,
		"diagnosis": summary,
		"status": "PASS — no changes needed" if not issues else "ISSUES_FOUND",
	}


def _scale_threshold(formula: str, pattern: str, factor: float) -> str:
	match = re.search(pattern, formula or "")
	if not match:
		return formula
	old_value = float(match.group(1))
	new_value = round(old_value * factor, 6)
	start, end = match.span(1)
	return formula[:start] + str(new_value) + formula[end:]


def fix(diagnosis: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
	"""Stage 4.2 - Portfolio Fix (spec §4.2 rule table). Applies exactly ONE
	structural change for the single highest-priority issue. "Add
	sector/geography diversification" has no field in this schema to attach
	to mechanically - it's returned as a `no_op` note rather than inventing
	a config key the rest of the engine wouldn't enforce."""
	issues = diagnosis.get("issues") or []
	if not issues:
		return None

	current_max_daily = get_path(config, MAX_DAILY_ORDERS_PATH)
	current_size = get_path(config, POSITION_SIZE_PATH) or ""
	problem = next((p for p in _FIX_PRIORITY if p in issues), issues[0])

	if problem == "fees_high":
		new_max_daily = max((current_max_daily or 1) - 1, 1)
		return {
			"problem": problem, "path": MAX_DAILY_ORDERS_PATH, "before": current_max_daily, "after": new_max_daily,
			"hypothesis": "Fees exceed 20% of gross P&L turnover - capping daily order count should "
			"reduce churn and let fees amortize over fewer, more deliberate entries.",
		}

	if problem in ("avg_positions_low", "utilization_low"):
		new_size = _scale_threshold(current_size, r"\*\s*([0-9.]+)\)\s*/", 0.8)
		return {
			"problem": problem, "path": POSITION_SIZE_PATH, "before": current_size, "after": new_size,
			"hypothesis": "Too little capital is deployed at once - shrinking the risk fraction per "
			"trade should free up room for more concurrent positions without changing total risk appetite.",
		}

	if problem == "correlation_high":
		return {
			"problem": problem, "no_op": True,
			"note": "Average correlation among concurrently-held positions exceeds 0.6, but this "
			"schema has no sector/geography field for a diversification constraint to attach to. "
			"Flagged for review rather than inventing a config key the engine wouldn't enforce.",
		}

	if problem == "fixed_sizing_high_variance":
		return {
			"problem": problem, "path": POSITION_SIZE_PATH, "before": current_size,
			"after": "(10000 * 0.01) / (atr_14[0] * 2.0)",
			"hypothesis": "Position sizing isn't volatility-adjusted - switching to ATR-scaled sizing "
			"(risk ~1% of capital per trade) should equalize risk across low- and high-volatility names.",
		}

	return None


def apply_fix(config: Dict[str, Any], fix_result: Dict[str, Any]) -> Dict[str, Any]:
	"""Deep-copy `config`, applying `fix_result["after"]` at `fix_result["path"]`
	- or return an unmodified deep copy if `fix_result` is a `no_op` note."""
	if fix_result.get("no_op"):
		return apply_overrides(config, {})
	return apply_overrides(config, {fix_result["path"]: fix_result["after"]})


# Stage 4.3 default Optuna search space - bounded to <=5 params (anti-pattern #3).
DEFAULT_PARAM_SPACE = [
	{"name": "position_size_risk_fraction", "path": POSITION_SIZE_PATH,
	 "type": "float", "low": 0.005, "high": 0.02, "pattern": r"\*\s*([0-9.]+)\)\s*/"},
	{"name": "max_positions", "path": MAX_POSITIONS_PATH, "type": "int", "low": 3, "high": 6},
	{"name": "max_daily_orders", "path": MAX_DAILY_ORDERS_PATH, "type": "int", "low": 1, "high": 3},
]


def optimize(
	config: Dict[str, Any],
	strategy_name: str,
	date_range: Tuple[str, str],
	n_trials: int,
	param_space: Optional[List[Dict[str, Any]]] = None,
	seed: Optional[int] = None,
	progress_callback=None,
	min_trades: int = 50,
):
	"""Stage 4.3 - Portfolio Optimization (spec §4.3). Maximizes Sharpe ratio
	subject to a max-drawdown cap and a minimum trade count, holding the
	locked watchlist/entry/exit fixed. `max_drawdown_pct` is in percentage
	points in this codebase, so the spec's `< 0.15` becomes `< 15`.
	`min_trades` defaults to the spec's literal floor but should be
	calibrated to the strategy's own baseline trade count for low-frequency
	strategies/universes."""
	param_space = param_space or [p for p in DEFAULT_PARAM_SPACE if get_path(config, p["path"]) is not None]
	return run_param_search(
		base_config=config,
		strategy_name=strategy_name,
		date_range=date_range,
		param_space=param_space,
		objective_metric="sharpe_ratio",
		n_trials=n_trials,
		direction="maximize",
		constraints=[{"metric": "max_drawdown_pct", "max": 15}, {"metric": "closed_trades", "min": min_trades}],
		seed=seed,
		progress_callback=progress_callback,
	)


def validate(
	old_metrics: Dict[str, Any],
	new_config: Dict[str, Any],
	strategy_name: str,
	date_range: Tuple[str, str],
	min_trades: int = 50,
) -> Dict[str, Any]:
	"""Stage 4.4 - Portfolio Validation (spec §4.4). Re-runs the backtest
	with the candidate portfolio settings (watchlist/entry/exit unchanged)
	and compares Sharpe, max drawdown, and fee ratio against the baseline."""
	scratch_name = f"{strategy_name}__portfolio_validation"
	result = run_scratch_backtest(new_config, scratch_name, date_range)
	backtest_dir = (result.get("output") or {}).get("backtest_dir")
	trade_records = build_trade_records(scratch_name, context={"backtest_dir": backtest_dir})
	new_metrics = (result.get("output") or {}).get("portfolio_metrics") or {}
	cleanup_scratch_backtest(scratch_name)

	old_sharpe = old_metrics.get("sharpe_ratio")
	new_sharpe = new_metrics.get("sharpe_ratio")
	old_dd = old_metrics.get("max_drawdown_pct")
	new_dd = new_metrics.get("max_drawdown_pct")
	new_fees_pct = compute_fees_pct_of_gross(trade_records, new_metrics.get("total_fees_paid"))

	dd_ok = True
	if old_dd is not None and new_dd is not None and old_dd > 0:
		dd_ok = new_dd <= old_dd * 1.2

	checks = {
		"sharpe_improved": bool(old_sharpe is not None and new_sharpe is not None and new_sharpe > old_sharpe),
		"drawdown_not_worsened": dd_ok,
		"trade_count_sufficient": len(trade_records) >= min_trades,
	}
	passed = result.get("status") == "success" and all(checks.values())

	return {
		"position_size": get_path(new_config, POSITION_SIZE_PATH),
		"max_positions": get_path(new_config, MAX_POSITIONS_PATH),
		"max_daily_orders": get_path(new_config, MAX_DAILY_ORDERS_PATH),
		"sharpe_before": old_sharpe,
		"sharpe_after": new_sharpe,
		"max_dd_before": old_dd,
		"max_dd_after": new_dd,
		"fees_pct_after": new_fees_pct,
		"trade_count_after": len(trade_records),
		"checks": checks,
		"status": "LOCKED" if passed else "REJECTED",
	}

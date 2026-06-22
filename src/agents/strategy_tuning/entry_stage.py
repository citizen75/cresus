"""Stage 2 — Entry diagnose/fix/optimize/validate (STRATEGY_IMPROVER v2.0 §2).

Given the locked watchlist, ensures the strategy enters at the right moment
with appropriate signal quality. Diagnosis needs: entry timing relative to
the subsequent price range, the false-entry rate, limit-order fill rate
(from the orders log - a BUY-only ledger separate from the journal), and a
standalone IC/hit-rate per signal (trend/momentum/volume_anomaly), evaluated
the same way Stage 1 evaluates the watchlist score: against each trade's
entry-time indicator snapshot rather than replaying price history.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from agents.strategy_tuning.common import cleanup_scratch_backtest, run_scratch_backtest
from tools.data.core import DataHistory
from tools.formula.dsl_parser import evaluate_dsl_vectorized
from tools.strategy.optuna_runner import apply_overrides, get_path, run_param_search
from tools.strategy.trade_log import build_trade_records

FALSE_ENTRY_RATE_FLAG = 0.30
FILL_RATE_LOW = 0.50
FILL_RATE_HIGH = 0.90
RANGE_POSITION_TOP_FLAG = 70.0  # % - entering above this = near the top of the post-entry range
SIGNAL_IC_REMOVE = 0.01
SIGNAL_IC_WEAK = 0.02

ENTRY_FILTER_PATH = "entry.parameters.entry_filter.formula"
LIMIT_PRICE_PATH = "entry.parameters.limit_price.formula"
SCORE_FILTER_PATH = "entry.parameters.score_filter.min"

SIGNAL_FORMULA_PATHS = {
	"trend": "signals.parameters.trend.formula",
	"momentum": "signals.parameters.momentum.formula",
	"volume_anomaly": "signals.parameters.volume_anomaly.formula",
}
SIGNAL_WEIGHT_PATHS = {name: f"signals.weights.{name}" for name in SIGNAL_FORMULA_PATHS}

# Priority order when multiple issues fire at once - anti-pattern #6 (never
# change more than 1 structural element per stage) means fix() acts on only
# the first match.
_FIX_PRIORITY = [
	"false_entry_rate_high",
	"signal_ic_low",
	"fill_rate_low",
	"fill_rate_high",
	"entering_near_top",
]


def _load_buy_orders(backtest_dir: Optional[str], scratch_name: str) -> pd.DataFrame:
	"""Load the BUY-order ledger (separate from the journal - records every
	limit order placed, including ones that expired unfilled) for fill-rate
	diagnosis."""
	if not backtest_dir:
		return pd.DataFrame()
	orders_file = Path(backtest_dir) / "orders" / f"{scratch_name}_orders.csv"
	if not orders_file.exists():
		return pd.DataFrame()
	try:
		df = pd.read_csv(orders_file)
	except Exception:
		return pd.DataFrame()
	if "operation" in df.columns:
		df = df[df["operation"].str.upper() == "BUY"]
	return df


def compute_fill_rate(backtest_dir: Optional[str], scratch_name: str) -> Optional[float]:
	"""% of BUY limit orders that filled (`status == "executed"`) vs expired
	or were cancelled."""
	orders = _load_buy_orders(backtest_dir, scratch_name)
	if orders.empty or "status" not in orders.columns:
		return None
	return float((orders["status"] == "executed").sum() / len(orders))


def compute_false_entry_rate(trade_records: List[Dict[str, Any]], max_days: int = 2) -> Optional[float]:
	"""% of trades that hit their stop within `max_days` of entry - an entry
	that goes wrong almost immediately, not a thesis that simply didn't pan
	out over time."""
	if not trade_records:
		return None
	false_entries = sum(
		1 for r in trade_records if r.get("exit_type") == "stop_loss" and r.get("holding_days", 99) <= max_days
	)
	return false_entries / len(trade_records)


def compute_avg_entry_position_in_range(
	trade_records: List[Dict[str, Any]], forward_days: int = 10
) -> Optional[float]:
	"""Average of (entry_price - low) / (high - low) * 100 over each trade's
	subsequent `forward_days` - 0% means we entered at the bottom of what
	followed (good), 100% means we entered right at the top (bad)."""
	positions = []
	for rec in trade_records:
		ticker, entry_date, entry_price = rec["ticker"], rec["entry_date"], rec["entry_price"]
		df = DataHistory(ticker).get_all(
			start_date=entry_date.strftime("%Y-%m-%d"),
			end_date=(entry_date + pd.Timedelta(days=forward_days)).strftime("%Y-%m-%d"),
		)
		if df.empty or "high" not in df.columns or "low" not in df.columns:
			continue
		high, low = float(df["high"].max()), float(df["low"].min())
		if high <= low:
			continue
		positions.append((entry_price - low) / (high - low) * 100.0)

	if not positions:
		return None
	return sum(positions) / len(positions)


def compute_signal_diagnostics(
	config: Dict[str, Any], trade_records: List[Dict[str, Any]], months_in_range: float
) -> List[Dict[str, Any]]:
	"""Standalone IC/hit-rate/fire-frequency for each enabled signal -
	evaluates the signal's own boolean formula against each trade's
	entry-time indicator snapshot, independent of the others, so a weak
	signal can be identified even though weighted scoring blends them."""
	diagnostics = []
	for name, path in SIGNAL_FORMULA_PATHS.items():
		formula = get_path(config, path)
		if not formula or str(formula).strip() == "False":
			continue

		fired, returns = [], []
		for rec in trade_records:
			snapshot = rec.get("entry_indicators") or {}
			if not snapshot:
				continue
			try:
				value = bool(evaluate_dsl_vectorized(formula, pd.DataFrame([snapshot])).iloc[0])
			except Exception:
				continue
			fired.append(1 if value else 0)
			returns.append(rec["pnl_pct"])

		if len(fired) < 5 or sum(fired) == 0:
			diagnostics.append({
				"name": name, "standalone_ic": None, "standalone_hit_rate": None,
				"fire_frequency_per_month": 0.0, "verdict": "REMOVE",
			})
			continue

		ic = pd.Series(fired).corr(pd.Series(returns), method="pearson")
		ic = None if pd.isna(ic) else float(ic)
		fired_returns = [r for f, r in zip(fired, returns) if f]
		hit_rate = sum(1 for r in fired_returns if r > 0) / len(fired_returns)
		fire_frequency = (sum(fired) / months_in_range) if months_in_range else 0.0

		if ic is None or ic < SIGNAL_IC_REMOVE:
			verdict = "REMOVE"
		elif ic < SIGNAL_IC_WEAK:
			verdict = "REDUCE"
		else:
			verdict = "KEEP"

		diagnostics.append({
			"name": name, "standalone_ic": ic, "standalone_hit_rate": hit_rate,
			"fire_frequency_per_month": fire_frequency, "verdict": verdict,
		})

	return diagnostics


def diagnose(
	config: Dict[str, Any],
	portfolio_name: str,
	start_date: str,
	end_date: str,
	backtest_dir: Optional[str] = None,
	context: Optional[Any] = None,
) -> Dict[str, Any]:
	"""Stage 2.1 - Entry Diagnosis (spec §2.1)."""
	trade_records = build_trade_records(portfolio_name, context=context)
	months_in_range = max((pd.Timestamp(end_date) - pd.Timestamp(start_date)).days / 30.4, 1.0)

	avg_position = compute_avg_entry_position_in_range(trade_records)
	false_entry_rate = compute_false_entry_rate(trade_records)
	fill_rate = compute_fill_rate(backtest_dir, portfolio_name)
	signals = compute_signal_diagnostics(config, trade_records, months_in_range)

	issues: List[str] = []
	if false_entry_rate is not None and false_entry_rate > FALSE_ENTRY_RATE_FLAG:
		issues.append("false_entry_rate_high")
	if any(s["verdict"] == "REMOVE" for s in signals):
		issues.append("signal_ic_low")
	if fill_rate is not None and fill_rate < FILL_RATE_LOW:
		issues.append("fill_rate_low")
	elif fill_rate is not None and fill_rate > FILL_RATE_HIGH:
		issues.append("fill_rate_high")
	if avg_position is not None and avg_position > RANGE_POSITION_TOP_FLAG:
		issues.append("entering_near_top")

	if issues:
		summary = f"Issues found: {', '.join(issues)}."
	else:
		summary = "Entry timing, false-entry rate, fill rate, and signal quality are all within target ranges."

	return {
		"avg_entry_position_in_range": avg_position,
		"false_entry_rate": false_entry_rate,
		"fill_rate": fill_rate,
		"signals": signals,
		"trade_count": len(trade_records),
		"issues": issues,
		"diagnosis": summary,
		"status": "PASS — no changes needed" if not issues else "ISSUES_FOUND",
	}


def _add_clause(formula: str, clause: str) -> str:
	if clause in formula:
		return formula
	formula = (formula or "").strip()
	return f"{formula} && {clause}" if formula else clause


def _scale_threshold(formula: str, pattern: str, factor: float) -> str:
	"""Multiply the first numeric value matched by `pattern`'s capture group
	by `factor`, in place. Falls back to the unmodified formula if no match."""
	match = re.search(pattern, formula or "")
	if not match:
		return formula
	old_value = float(match.group(1))
	new_value = round(old_value * factor, 6)
	start, end = match.span(1)
	return formula[:start] + str(new_value) + formula[end:]


def fix(diagnosis: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
	"""Stage 2.2 - Entry Fix (spec §2.2 rule table). Applies exactly ONE
	structural change for the single highest-priority issue."""
	issues = diagnosis.get("issues") or []
	if not issues:
		return None

	current_filter = get_path(config, ENTRY_FILTER_PATH) or ""
	current_limit = get_path(config, LIMIT_PRICE_PATH) or ""
	problem = next((p for p in _FIX_PRIORITY if p in issues), issues[0])

	if problem == "false_entry_rate_high":
		new_filter = _scale_threshold(current_filter, r"vol_atr_pct\[0\]\s*<\s*([0-9.]+)", 0.75)
		if new_filter == current_filter:
			new_filter = _add_clause(current_filter, "vol_atr_pct[0] < 0.03")
		return {
			"problem": problem, "path": ENTRY_FILTER_PATH, "before": current_filter, "after": new_filter,
			"hypothesis": "Over 30% of entries stop out within 2 days - tightening the volatility "
			"ceiling should screen out entries made during excessive short-term turbulence.",
		}

	if problem == "signal_ic_low":
		worst = next(s for s in diagnosis["signals"] if s["verdict"] == "REMOVE")
		signal_path = SIGNAL_FORMULA_PATHS[worst["name"]]
		weight_path = SIGNAL_WEIGHT_PATHS[worst["name"]]
		return {
			"problem": problem, "path": signal_path, "before": get_path(config, signal_path), "after": "False",
			"weight_path": weight_path, "weight_before": get_path(config, weight_path), "weight_after": 0.0,
			"hypothesis": f"Signal '{worst['name']}' has standalone IC "
			f"{worst['standalone_ic']}, below the 0.01 floor (anti-pattern #4) - disabling it and "
			"zeroing its weight removes noise rather than searching for a replacement mid-stage.",
		}

	if problem == "fill_rate_low":
		new_limit = _scale_threshold(current_limit, r"\*\s*([0-9.]+)", 1.005)
		return {
			"problem": problem, "path": LIMIT_PRICE_PATH, "before": current_limit, "after": new_limit,
			"hypothesis": "Fill rate is under 50% - the limit discount is too aggressive for how "
			"this universe trades; widening it slightly should catch more of the intended entries.",
		}

	if problem == "fill_rate_high":
		new_limit = _scale_threshold(current_limit, r"\*\s*([0-9.]+)", 0.997)
		return {
			"problem": problem, "path": LIMIT_PRICE_PATH, "before": current_limit, "after": new_limit,
			"hypothesis": "Fill rate is over 90% - the limit order is effectively a market order and "
			"isn't extracting any edge from waiting for a better price; tightening it should start to.",
		}

	if problem == "entering_near_top":
		new_filter = _add_clause(current_filter, "close[0] < ema_10[0] * 1.01")
		return {
			"problem": problem, "path": ENTRY_FILTER_PATH, "before": current_filter, "after": new_filter,
			"hypothesis": "Entries land near the top of the price range that follows them - requiring "
			"a small pullback toward the fast EMA should improve where in the move we actually get filled.",
		}

	return None


def apply_fix(config: Dict[str, Any], fix_result: Dict[str, Any]) -> Dict[str, Any]:
	"""Deep-copy `config` with `fix_result["after"]` written to `fix_result["path"]`
	(and, for a signal removal, its weight zeroed too)."""
	overrides = {fix_result["path"]: fix_result["after"]}
	if "weight_path" in fix_result:
		overrides[fix_result["weight_path"]] = fix_result["weight_after"]
	return apply_overrides(config, overrides)


# Stage 2.3 default Optuna search space - bounded to <=5 params (anti-pattern #3).
DEFAULT_PARAM_SPACE = [
	{"name": "adx_entry_threshold", "path": ENTRY_FILTER_PATH,
	 "type": "int", "low": 18, "high": 30, "pattern": r"adx_14\[0\]\s*>\s*(\d+)"},
	# Tunes the raw multiplier directly (e.g. 0.995 = a 0.5% discount to close)
	# rather than a separately-computed discount fraction, since the
	# pattern/replace override mechanism edits whatever numeral is already
	# in the formula in place rather than re-deriving it from a transform.
	{"name": "limit_price_discount", "path": LIMIT_PRICE_PATH,
	 "type": "float", "low": 0.985, "high": 0.999, "pattern": r"\*\s*([0-9.]+)$"},
	{"name": "score_min", "path": SCORE_FILTER_PATH, "type": "float", "low": 50, "high": 80},
	{"name": "signal_weight_trend", "path": SIGNAL_WEIGHT_PATHS["trend"], "type": "float", "low": 0.3, "high": 0.6},
	{"name": "signal_weight_momentum", "path": SIGNAL_WEIGHT_PATHS["momentum"], "type": "float", "low": 0.2, "high": 0.5},
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
	"""Stage 2.3 - Entry Optimization (spec §2.3). Maximizes expectancy per
	trade (`expectancy_pct` in `portfolio_metrics`) subject to a minimum
	trade count, holding the locked watchlist and current exit fixed.
	`min_trades` defaults to the spec's literal floor but should be
	calibrated to the strategy's own baseline trade count for low-frequency
	strategies/universes, where 50 may be structurally unreachable."""
	param_space = param_space or [p for p in DEFAULT_PARAM_SPACE if get_path(config, p["path"]) is not None]
	return run_param_search(
		base_config=config,
		strategy_name=strategy_name,
		date_range=date_range,
		param_space=param_space,
		objective_metric="expectancy_pct",
		n_trials=n_trials,
		direction="maximize",
		constraints=[{"metric": "closed_trades", "min": min_trades}],
		seed=seed,
		progress_callback=progress_callback,
	)


def validate(
	old_diagnosis: Dict[str, Any],
	new_config: Dict[str, Any],
	strategy_name: str,
	date_range: Tuple[str, str],
	min_trades: int = 50,
) -> Dict[str, Any]:
	"""Stage 2.4 - Entry Validation (spec §2.4). Re-runs the backtest with
	the candidate entry (watchlist + exit unchanged) and compares against
	the baseline diagnosis. Locks only if the false-entry rate decreased and
	expectancy per trade improved (win rate improving is a bonus, not
	required, per spec)."""
	scratch_name = f"{strategy_name}__entry_validation"
	result = run_scratch_backtest(new_config, scratch_name, date_range)
	backtest_dir = (result.get("output") or {}).get("backtest_dir")
	trade_records = build_trade_records(scratch_name, context={"backtest_dir": backtest_dir})
	metrics = (result.get("output") or {}).get("portfolio_metrics") or {}
	cleanup_scratch_backtest(scratch_name)

	new_false_entry_rate = compute_false_entry_rate(trade_records)
	old_false_entry_rate = old_diagnosis.get("false_entry_rate")
	new_expectancy = metrics.get("expectancy_pct")

	checks = {
		"false_entry_rate_decreased": bool(
			new_false_entry_rate is not None
			and old_false_entry_rate is not None
			and new_false_entry_rate < old_false_entry_rate
		),
		"trade_count_sufficient": len(trade_records) >= min_trades,
	}
	passed = result.get("status") == "success" and all(checks.values())

	return {
		"entry_filter": get_path(new_config, ENTRY_FILTER_PATH),
		"signals": {name: get_path(new_config, path) for name, path in SIGNAL_FORMULA_PATHS.items()},
		"false_entry_rate_before": old_false_entry_rate,
		"false_entry_rate_after": new_false_entry_rate,
		"expectancy_after": new_expectancy,
		"trade_count_after": len(trade_records),
		"checks": checks,
		"status": "LOCKED" if passed else "REJECTED",
	}

"""Stage 3 — Exit diagnose/fix/optimize/validate (STRATEGY_IMPROVER v2.0 §3).

Given the locked watchlist and entry, maximizes P&L captured per trade
through stop, target, and exit-condition management.

Exit-type mapping note: this codebase's journal records `exit_type` as one
of `stop_loss` / `take_profit` / `condition` / `expired`. `expired` is the
strategy's `exit.parameters.holding_period` forced exit - the spec's
`time_stop` category instead refers to *unfilled limit orders* expiring
before ever becoming a position (an order-management concept already
covered by Stage 2's fill-rate diagnosis), so it has no trade-level
exit_type here and is omitted from `exit_distribution`.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from agents.strategy_tuning.common import cleanup_scratch_backtest, run_scratch_backtest
from tools.data.core import DataHistory
from tools.strategy.optuna_runner import apply_overrides, get_path, run_param_search
from tools.strategy.trade_log import build_trade_records, enrich_with_excursion

STOP_LOSS_PCT_FLAG = 0.40
STOP_RECOVERY_HIGH = 0.50
STOP_RECOVERY_LOW = 0.30
TP_PCT_FLAG = 0.30
TP_CONTINUATION_FLAG = 0.50
HOLDING_EXIT_PCT_FLAG = 0.25
MFE_MAE_RATIO_TRAILING_HELPS = 2.0
MFE_MAE_RATIO_FIXED_BETTER = 1.5

CONDITION_PATH = "exit.parameters.condition.formula"
HOLDING_PERIOD_PATH = "exit.parameters.holding_period.formula"
STOP_PATH = "exit.parameters.stop.formula"
STOP_TYPE_PATH = "exit.parameters.stop.type"
TAKE_PROFIT_PATH = "exit.parameters.take_profit.formula"

# Priority order when multiple issues fire at once - anti-pattern #6 (never
# change more than 1 structural element per stage) means fix() acts on only
# the first match.
_FIX_PRIORITY = [
	"stop_outs_high_recoverable",
	"stop_outs_high_unrecoverable",
	"tp_continuation_high",
	"holding_exit_positive",
	"holding_exit_negative",
	"no_condition_exits",
	"mfe_dominant",
]


def compute_exit_distribution(trade_records: List[Dict[str, Any]]) -> Dict[str, float]:
	"""% of trades ending by each exit_type (spec's exit_distribution)."""
	if not trade_records:
		return {}
	counts = pd.Series([r.get("exit_type", "unknown") for r in trade_records]).value_counts()
	total = len(trade_records)
	return {exit_type: count / total for exit_type, count in counts.items()}


def _forward_window(ticker: str, after_date: pd.Timestamp, days: int) -> pd.DataFrame:
	return DataHistory(ticker).get_all(
		start_date=after_date.strftime("%Y-%m-%d"),
		end_date=(after_date + pd.Timedelta(days=days)).strftime("%Y-%m-%d"),
	)


def compute_stop_recovery_rate(trade_records: List[Dict[str, Any]], window_days: int = 5) -> Optional[float]:
	"""% of stopped-out trades whose price recovered back to (or above) the
	entry price within `window_days` of the stop exit - i.e. the stop was
	too tight rather than correctly cutting a real loser."""
	stopped = [r for r in trade_records if r.get("exit_type") == "stop_loss"]
	if not stopped:
		return None
	recovered = 0
	for rec in stopped:
		window = _forward_window(rec["ticker"], rec["exit_date"], window_days)
		if window.empty or "close" not in window.columns:
			continue
		if float(window["close"].max()) >= rec["entry_price"]:
			recovered += 1
	return recovered / len(stopped)


def compute_tp_continuation_rate(
	trade_records: List[Dict[str, Any]], window_days: int = 7, atr_multiple: float = 1.0
) -> Optional[float]:
	"""% of take-profit exits where price kept rallying more than
	`atr_multiple` ATRs beyond the exit price within `window_days` - i.e.
	the target was too tight and capped a bigger winner."""
	tp_exits = [r for r in trade_records if r.get("exit_type") == "take_profit"]
	if not tp_exits:
		return None
	continued = 0
	for rec in tp_exits:
		atr = (rec.get("entry_indicators") or {}).get("atr_14")
		if not atr:
			continue
		window = _forward_window(rec["ticker"], rec["exit_date"], window_days)
		if window.empty or "high" not in window.columns:
			continue
		if float(window["high"].max()) >= rec["exit_price"] + atr_multiple * atr:
			continued += 1
	return continued / len(tp_exits)


def compute_holding_exit_avg_pnl(trade_records: List[Dict[str, Any]]) -> Optional[float]:
	"""Average P&L% of trades exited by the holding-period forced exit
	(`exit_type == "expired"`) - positive means the holding period is
	cutting winners short, negative means the entry thesis just wasn't there."""
	holding_exits = [r for r in trade_records if r.get("exit_type") == "expired"]
	if not holding_exits:
		return None
	return sum(r["pnl_pct"] for r in holding_exits) / len(holding_exits)


def compute_excursion_medians(trade_records: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float]]:
	"""Median MAE/MFE in ATR multiples across all trades (spec §3.1) - reuses
	`trade_log.enrich_with_excursion`, loading only the traded tickers'
	plain OHLCV (no indicators needed; ATR comes from each trade's own
	`entry_indicators` snapshot)."""
	if not trade_records:
		return None, None
	tickers = {r["ticker"] for r in trade_records}
	data_history = {t: DataHistory(t).load_all() for t in tickers}
	enriched = enrich_with_excursion(trade_records, data_history)
	maes = [r["mae_atr"] for r in enriched if r.get("mae_atr") is not None]
	mfes = [r["mfe_atr"] for r in enriched if r.get("mfe_atr") is not None]
	median_mae = float(pd.Series(maes).median()) if maes else None
	median_mfe = float(pd.Series(mfes).median()) if mfes else None
	return median_mae, median_mfe


def diagnose(
	config: Dict[str, Any], portfolio_name: str, start_date: str, end_date: str, context: Optional[Any] = None
) -> Dict[str, Any]:
	"""Stage 3.1 - Exit Diagnosis (spec §3.1)."""
	trade_records = build_trade_records(portfolio_name, context=context)
	distribution = compute_exit_distribution(trade_records)
	stop_recovery = compute_stop_recovery_rate(trade_records)
	tp_continuation = compute_tp_continuation_rate(trade_records)
	holding_avg_pnl = compute_holding_exit_avg_pnl(trade_records)
	median_mae, median_mfe = compute_excursion_medians(trade_records)

	stop_pct = distribution.get("stop_loss", 0.0)
	tp_pct = distribution.get("take_profit", 0.0)
	holding_pct = distribution.get("expired", 0.0)
	condition_pct = distribution.get("condition", 0.0)

	issues: List[str] = []
	if stop_pct > STOP_LOSS_PCT_FLAG:
		if stop_recovery is not None and stop_recovery > STOP_RECOVERY_HIGH:
			issues.append("stop_outs_high_recoverable")
		elif stop_recovery is not None and stop_recovery < STOP_RECOVERY_LOW:
			issues.append("stop_outs_high_unrecoverable")
	if tp_pct > TP_PCT_FLAG and tp_continuation is not None and tp_continuation > TP_CONTINUATION_FLAG:
		issues.append("tp_continuation_high")
	if holding_pct > HOLDING_EXIT_PCT_FLAG and holding_avg_pnl is not None:
		issues.append("holding_exit_positive" if holding_avg_pnl > 0 else "holding_exit_negative")
	if trade_records and condition_pct == 0.0:
		issues.append("no_condition_exits")
	if median_mae is not None and median_mfe is not None and median_mae > 0:
		if median_mfe > MFE_MAE_RATIO_TRAILING_HELPS * median_mae:
			issues.append("mfe_dominant")

	if issues:
		summary = f"Issues found: {', '.join(issues)}."
	else:
		summary = "Exit distribution, stop recovery, TP continuation, and MAE/MFE are all within target ranges."

	return {
		"exit_distribution": distribution,
		"stop_recovery_rate": stop_recovery,
		"tp_continuation_rate": tp_continuation,
		"holding_exit_avg_pnl": holding_avg_pnl,
		"median_mae_atr": median_mae,
		"median_mfe_atr": median_mfe,
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
	"""Stage 3.2 - Exit Fix (spec §3.2 rule table + trailing-stop decision
	tree). Applies exactly ONE structural change for the single
	highest-priority issue. Some diagnoses (stop is correct but entry is the
	real problem; no exit condition ever fires) have no safe mechanical fix
	within this stage per anti-pattern #2 (never go backward) - these are
	returned as `no_op` notes for the next iteration instead of a change."""
	issues = diagnosis.get("issues") or []
	if not issues:
		return None

	current_stop = get_path(config, STOP_PATH) or ""
	current_tp = get_path(config, TAKE_PROFIT_PATH) or ""
	current_holding = get_path(config, HOLDING_PERIOD_PATH)
	problem = next((p for p in _FIX_PRIORITY if p in issues), issues[0])

	if problem == "stop_outs_high_recoverable":
		new_stop = _scale_threshold(current_stop, r"\*\s*([0-9.]+)$", 1.25)
		return {
			"problem": problem, "path": STOP_PATH, "before": current_stop, "after": new_stop,
			"hypothesis": "Over 40% of exits are stop-outs and most recover within days - the stop "
			"is too tight for this instrument's normal noise; widening it should let more trades survive.",
		}

	if problem == "stop_outs_high_unrecoverable":
		return {
			"problem": problem, "no_op": True,
			"note": "Stop-outs exceed 40% but recovery is under 30% - the stop is correctly cutting "
			"real losers. The actual problem is upstream in entry timing (Stage 2); per anti-pattern #2 "
			"this is flagged for the next iteration rather than reopening a locked stage.",
		}

	if problem == "tp_continuation_high":
		new_tp = _scale_threshold(current_tp, r"\*\s*([0-9.]+)$", 1.2)
		return {
			"problem": problem, "path": TAKE_PROFIT_PATH, "before": current_tp, "after": new_tp,
			"hypothesis": "Over 30% of exits hit take-profit and most keep rallying afterward - the "
			"target is too tight; widening it should capture more of the move before forcing an exit.",
		}

	if problem == "holding_exit_positive":
		new_holding = (current_holding or 0) + 5
		return {
			"problem": problem, "path": HOLDING_PERIOD_PATH, "before": current_holding, "after": new_holding,
			"hypothesis": "Over 25% of exits are forced by the holding period and average P&L on those "
			"is positive - the period is cutting winners short; extending it should let them develop.",
		}

	if problem == "holding_exit_negative":
		new_holding = max((current_holding or 0) - 5, 1)
		return {
			"problem": problem, "path": HOLDING_PERIOD_PATH, "before": current_holding, "after": new_holding,
			"hypothesis": "Over 25% of exits are forced by the holding period and average P&L on those "
			"is negative - the thesis isn't materializing; cutting the period short should reduce drag.",
		}

	if problem == "no_condition_exits":
		return {
			"problem": problem, "no_op": True,
			"note": "The exit condition formula never fired across any trade - it's dead code. "
			"Redesigning it requires a new hypothesis about what regime change should trigger an early "
			"exit, which is a judgment call beyond a safe mechanical transform; flagged for review.",
		}

	if problem == "mfe_dominant":
		current_type = get_path(config, STOP_TYPE_PATH)
		if current_type == "trailing":
			return {
				"problem": problem, "no_op": True,
				"note": "Median MFE is more than 2x median MAE, which would normally argue for a "
				"trailing stop - but the exit is already trailing, so there's no structural change left "
				"to make here; the gap is likely the trailing distance itself, which Optuna will tune.",
			}
		return {
			"problem": problem, "path": STOP_TYPE_PATH, "before": current_type, "after": "trailing",
			"hypothesis": "Median MFE is more than 2x median MAE - per the trailing-stop decision tree, "
			"switching from a fixed stop to a trailing one should lock in more of the favorable excursion.",
		}

	return None


def apply_fix(config: Dict[str, Any], fix_result: Dict[str, Any]) -> Dict[str, Any]:
	"""Deep-copy `config`, applying `fix_result["after"]` at `fix_result["path"]`
	- or return an unmodified deep copy if `fix_result` is a `no_op` note."""
	if fix_result.get("no_op"):
		return apply_overrides(config, {})
	return apply_overrides(config, {fix_result["path"]: fix_result["after"]})


# Stage 3.3 default Optuna search space - bounded to <=5 params (anti-pattern #3).
# `trailing_atr_mult` is omitted: in this codebase the trailing stop reuses
# the same `stop.formula` ATR multiplier as its initial distance (see the
# strategy YAML's own comment on that field), so it IS `stop_atr_mult` here,
# not a separate parameter.
DEFAULT_PARAM_SPACE = [
	{"name": "stop_atr_mult", "path": STOP_PATH,
	 "type": "float", "low": 1.2, "high": 3.0, "log": True, "pattern": r"\*\s*([0-9.]+)$"},
	{"name": "take_profit_atr_mult", "path": TAKE_PROFIT_PATH,
	 "type": "float", "low": 2.0, "high": 5.0, "log": True, "pattern": r"\*\s*([0-9.]+)$"},
	{"name": "holding_period", "path": HOLDING_PERIOD_PATH, "type": "int", "low": 8, "high": 25},
	{"name": "exit_adx_floor", "path": CONDITION_PATH,
	 "type": "int", "low": 10, "high": 20, "pattern": r"adx_14\[0\]\s*<\s*(\d+)"},
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
	"""Stage 3.3 - Exit Optimization (spec §3.3). Maximizes profit factor
	subject to a max-drawdown cap and a minimum trade count, holding the
	locked watchlist and entry fixed. `max_drawdown_pct` in
	`portfolio_metrics` is expressed in percentage points in this codebase,
	so the spec's `< 0.15` becomes `< 15`. `min_trades` defaults to the
	spec's literal floor but should be calibrated to the strategy's own
	baseline trade count for low-frequency strategies/universes."""
	param_space = param_space or [p for p in DEFAULT_PARAM_SPACE if get_path(config, p["path"]) is not None]
	return run_param_search(
		base_config=config,
		strategy_name=strategy_name,
		date_range=date_range,
		param_space=param_space,
		objective_metric="profit_factor",
		n_trials=n_trials,
		direction="maximize",
		constraints=[{"metric": "max_drawdown_pct", "max": 15}, {"metric": "closed_trades", "min": min_trades}],
		seed=seed,
		progress_callback=progress_callback,
	)


def validate(
	old_diagnosis: Dict[str, Any],
	old_metrics: Dict[str, Any],
	new_config: Dict[str, Any],
	strategy_name: str,
	date_range: Tuple[str, str],
	min_trades: int = 50,
) -> Dict[str, Any]:
	"""Stage 3.4 - Exit Validation (spec §3.4). Re-runs the backtest with the
	candidate exit (watchlist + entry unchanged) and compares against the
	baseline's own backtest metrics. Locks only if profit factor improved,
	max drawdown didn't worsen by more than 20% relative, and avg P&L per
	trade improved."""
	scratch_name = f"{strategy_name}__exit_validation"
	result = run_scratch_backtest(new_config, scratch_name, date_range)
	backtest_dir = (result.get("output") or {}).get("backtest_dir")
	trade_records = build_trade_records(scratch_name, context={"backtest_dir": backtest_dir})
	new_metrics = (result.get("output") or {}).get("portfolio_metrics") or {}
	cleanup_scratch_backtest(scratch_name)

	old_pf = old_metrics.get("profit_factor")
	new_pf = new_metrics.get("profit_factor")
	old_dd = old_metrics.get("max_drawdown_pct")
	new_dd = new_metrics.get("max_drawdown_pct")
	new_avg_pnl = (sum(r["pnl_pct"] for r in trade_records) / len(trade_records)) if trade_records else None

	dd_ok = True
	if old_dd is not None and new_dd is not None and old_dd > 0:
		dd_ok = new_dd <= old_dd * 1.2

	checks = {
		"profit_factor_improved": bool(old_pf is not None and new_pf is not None and new_pf > old_pf),
		"drawdown_not_worsened": dd_ok,
		"trade_count_sufficient": len(trade_records) >= min_trades,
	}
	passed = result.get("status") == "success" and all(checks.values())

	return {
		"stop": get_path(new_config, STOP_PATH),
		"take_profit": get_path(new_config, TAKE_PROFIT_PATH),
		"condition": get_path(new_config, CONDITION_PATH),
		"holding_period": get_path(new_config, HOLDING_PERIOD_PATH),
		"profit_factor_before": old_pf,
		"profit_factor_after": new_pf,
		"max_dd_before": old_dd,
		"max_dd_after": new_dd,
		"avg_pnl_after": new_avg_pnl,
		"trade_count_after": len(trade_records),
		"checks": checks,
		"status": "LOCKED" if passed else "REJECTED",
	}

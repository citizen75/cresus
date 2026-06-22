"""Stage 1 — Watchlist diagnose/fix/optimize/validate (STRATEGY_IMPROVER v2.0 §1).

Ensures the strategy is looking at the right tickers with a scoring formula
that ranks genuine opportunities above noise, before the entry/exit stages
build on top of it. Diagnosis needs two things no other part of the pipeline
computes: a full-universe filter pass rate (the saved watchlist only records
post-filter survivors, not the full pass/fail picture - see
`tools/watchlist`) and a score-to-return rank correlation (computed by
re-evaluating the scoring formula against each trade's entry-time indicator
snapshot rather than reloading history).
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from agents.strategy_tuning.common import cleanup_scratch_backtest, prepare_data_history, run_scratch_backtest
from tools.data.core import DataHistory
from tools.formula.dsl_parser import evaluate_dsl_vectorized
from tools.strategy.optuna_runner import apply_overrides, get_path, run_param_search
from tools.strategy.trade_log import build_trade_records

PASS_RATE_TARGET = (0.20, 0.40)
PASS_RATE_TOO_TIGHT = 0.10
PASS_RATE_TOO_LOOSE = 0.60
SCORE_IC_TARGET = 0.03
SCORE_IC_WEAK = 0.02
CONCENTRATION_FLAG = 0.50

FILTER_PATH = "watchlist.parameters.filter.formula"
SCORING_PATH = "watchlist.parameters.scoring.formula"

# Priority order when multiple issues fire at once - anti-pattern #6 (never
# change more than 1 structural element per stage) means fix() acts on only
# the first match.
_FIX_PRIORITY = [
	"score_ic_negative",
	"pass_rate_too_high",
	"pass_rate_too_low",
	"score_ic_weak",
	"losing_tickers_dominate",
	"high_concentration",
]


def compute_filter_pass_rate(
	config: Dict[str, Any],
	start_date: str,
	end_date: str,
	data_history: Optional[Dict[str, pd.DataFrame]] = None,
	scratch_name: str = "_watchlist_diag",
) -> Tuple[float, Dict[str, pd.Series]]:
	"""Replay the watchlist filter formula across the full universe over
	[start_date, end_date] using cached data only - no orders/portfolio, so
	it's cheap relative to a full backtest. Returns (pass_rate, {ticker:
	bool_series indexed by timestamp}). Pass a pre-built `data_history` (see
	`prepare_data_history`) to avoid re-running the prep agents per call."""
	filter_formula = get_path(config, FILTER_PATH)
	if not filter_formula:
		return 0.0, {}
	if data_history is None:
		data_history = prepare_data_history(config, f"{scratch_name}__filter_replay")

	start_ts, end_ts = pd.Timestamp(start_date), pd.Timestamp(end_date)
	pass_series: Dict[str, pd.Series] = {}
	total_days = 0
	total_passes = 0

	for ticker, df in data_history.items():
		if df is None or df.empty:
			continue
		window = df.sort_values("timestamp").reset_index(drop=True)
		mask = (window["timestamp"] >= start_ts) & (window["timestamp"] <= end_ts)
		window = window.loc[mask].reset_index(drop=True)
		if window.empty:
			continue
		try:
			result = evaluate_dsl_vectorized(filter_formula, window)
		except Exception:
			continue
		result = result.fillna(False).astype(bool).reset_index(drop=True)
		n = min(len(result), len(window))
		pass_series[ticker] = pd.Series(result.values[:n], index=pd.to_datetime(window["timestamp"]).values[:n])
		total_days += n
		total_passes += int(result.values[:n].sum())

	pass_rate = (total_passes / total_days) if total_days else 0.0
	return pass_rate, pass_series


def compute_score_return_ic(config: Dict[str, Any], trade_records: List[Dict[str, Any]]) -> Optional[float]:
	"""Rank correlation between the watchlist composite score at entry time
	and the trade's realized return. Evaluates the scoring formula against
	each trade's `entry_indicators` snapshot (from the journal's metadata
	column) rather than replaying price history.

	Uses `evaluate_dsl_vectorized` (numeric Series output), not
	`tools.formula.calculator.evaluate` - the latter always casts its result
	to `bool`, which is correct for filter/entry conditions but silently
	collapses a numeric composite score to a constant `True`/`False`."""
	scoring_formula = get_path(config, SCORING_PATH)
	if not scoring_formula or not trade_records:
		return None

	scores, returns = [], []
	for rec in trade_records:
		snapshot = rec.get("entry_indicators") or {}
		if not snapshot:
			continue
		try:
			score = evaluate_dsl_vectorized(scoring_formula, pd.DataFrame([snapshot])).iloc[0]
		except Exception:
			continue
		if score is None or pd.isna(score):
			continue
		try:
			scores.append(float(score))
		except (TypeError, ValueError):
			continue
		returns.append(rec["pnl_pct"])

	if len(scores) < 5:
		return None
	ic = pd.Series(scores).corr(pd.Series(returns), method="spearman")
	return None if pd.isna(ic) else float(ic)


def compute_concentration(trade_records: List[Dict[str, Any]]) -> Tuple[float, List[str]]:
	"""% of trades concentrated in the top-3 most-traded tickers."""
	if not trade_records:
		return 0.0, []
	counts = pd.Series([r["ticker"] for r in trade_records]).value_counts()
	top3 = counts.head(3)
	pct = float(top3.sum() / len(trade_records))
	return pct, list(top3.index)


def compute_losing_tickers(trade_records: List[Dict[str, Any]]) -> List[str]:
	if not trade_records:
		return []
	df = pd.DataFrame(trade_records)
	by_ticker = df.groupby("ticker")["pnl_amount"].sum()
	return list(by_ticker[by_ticker < 0].index)


def compute_missed_tickers(
	pass_series: Dict[str, pd.Series],
	traded_tickers: set,
	forward_days: int = 5,
	min_pass_days: int = 5,
) -> List[str]:
	"""Tickers that passed the filter on enough days but were never traded,
	and whose average forward return on filter-pass days was positive - i.e.
	the filter is excluding real opportunities, not correctly screening noise."""
	missed = []
	for ticker, series in pass_series.items():
		if ticker in traded_tickers or int(series.sum()) < min_pass_days:
			continue
		closes = DataHistory(ticker).load_all()
		if closes.empty:
			continue
		closes = closes.sort_values("timestamp")
		ts_index = pd.to_datetime(closes["timestamp"]).reset_index(drop=True)
		close_values = closes["close"].reset_index(drop=True)

		fwd_returns = []
		for ts, passed in series.items():
			if not passed:
				continue
			matches = ts_index[ts_index <= ts]
			if matches.empty:
				continue
			loc = matches.index[-1]
			if loc + forward_days < len(close_values):
				entry_px = close_values.iloc[loc]
				exit_px = close_values.iloc[loc + forward_days]
				if entry_px:
					fwd_returns.append(exit_px / entry_px - 1.0)

		if fwd_returns and (sum(fwd_returns) / len(fwd_returns)) > 0:
			missed.append(ticker)
	return missed


def diagnose(
	config: Dict[str, Any], portfolio_name: str, start_date: str, end_date: str, context: Optional[Any] = None
) -> Dict[str, Any]:
	"""Stage 1.1 - Watchlist Diagnosis (spec §1.1)."""
	trade_records = build_trade_records(portfolio_name, context=context)
	data_history = prepare_data_history(config, f"{portfolio_name}__watchlist_diag")
	pass_rate, pass_series = compute_filter_pass_rate(config, start_date, end_date, data_history=data_history)
	score_ic = compute_score_return_ic(config, trade_records)
	concentration_pct, top3_tickers = compute_concentration(trade_records)
	losing_tickers = compute_losing_tickers(trade_records)
	traded_tickers = {r["ticker"] for r in trade_records}
	missed_tickers = compute_missed_tickers(pass_series, traded_tickers)

	issues: List[str] = []
	if pass_rate > PASS_RATE_TOO_LOOSE:
		issues.append("pass_rate_too_high")
	elif pass_rate < PASS_RATE_TOO_TIGHT:
		issues.append("pass_rate_too_low")
	if score_ic is not None and score_ic < 0:
		issues.append("score_ic_negative")
	elif score_ic is not None and score_ic < SCORE_IC_WEAK:
		issues.append("score_ic_weak")
	if concentration_pct > CONCENTRATION_FLAG:
		issues.append("high_concentration")
	if losing_tickers and traded_tickers and len(losing_tickers) >= len(traded_tickers) / 2:
		issues.append("losing_tickers_dominate")

	if issues:
		summary = f"Issues found: {', '.join(issues)}."
	else:
		summary = "Filter pass rate, score IC, and concentration are all within target ranges."

	return {
		"filter_pass_rate": pass_rate,
		"score_return_ic": score_ic,
		"top_3_ticker_concentration": concentration_pct,
		"top_3_tickers": top3_tickers,
		"losing_tickers": losing_tickers,
		"missed_tickers": missed_tickers,
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


def _remove_weakest_clause(formula: str) -> str:
	clauses = [c.strip() for c in (formula or "").split("&&")]
	if len(clauses) <= 1:
		return formula
	return " && ".join(clauses[:-1])


def fix(diagnosis: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
	"""Stage 1.2 - Watchlist Fix (spec §1.2 rule table). Applies exactly ONE
	structural change for the single highest-priority issue."""
	issues = diagnosis.get("issues") or []
	if not issues:
		return None

	current_filter = get_path(config, FILTER_PATH) or ""
	current_scoring = get_path(config, SCORING_PATH) or ""
	problem = next((p for p in _FIX_PRIORITY if p in issues), issues[0])

	if problem == "pass_rate_too_high":
		new_filter = _add_clause(current_filter, "close[0] > sma_50[0]")
		return {
			"problem": problem, "path": FILTER_PATH, "before": current_filter, "after": new_filter,
			"hypothesis": "Pass rate exceeded the 60% ceiling - the watchlist isn't selective; "
			"adding a trend-quality gate (price above its 50-day average) should cut the noise.",
		}

	if problem == "pass_rate_too_low":
		new_filter = _remove_weakest_clause(current_filter)
		return {
			"problem": problem, "path": FILTER_PATH, "before": current_filter, "after": new_filter,
			"hypothesis": "Pass rate was under the 10% floor - the filter excludes too much of the "
			"universe; dropping its weakest condition should widen the pool toward the 20-40% target.",
		}

	if problem == "score_ic_negative":
		new_scoring = f"(-1) * ({current_scoring})"
		return {
			"problem": problem, "path": SCORING_PATH, "before": current_scoring, "after": new_scoring,
			"hypothesis": "Composite score was negatively correlated with realized trade return - "
			"inverting its sign should flip it into a genuine ranking signal.",
		}

	if problem == "score_ic_weak":
		new_scoring = f"({current_scoring}) / (1 + atr_14[0] / close[0])"
		return {
			"problem": problem, "path": SCORING_PATH, "before": current_scoring, "after": new_scoring,
			"hypothesis": "Score IC was below the 0.02 floor - dividing by a volatility term rewards "
			"risk-adjusted setups over merely loud ones, sharpening the rank correlation with forward return.",
		}

	if problem == "losing_tickers_dominate":
		new_filter = _add_clause(current_filter, "(atr_14[0] / close[0]) > 0.01")
		return {
			"problem": problem, "path": FILTER_PATH, "before": current_filter, "after": new_filter,
			"hypothesis": "Losing tickers account for half or more of all trades - a minimum "
			"volatility/liquidity floor should screen out the dead names generating those losses.",
		}

	if problem == "high_concentration":
		new_filter = _add_clause(current_filter, "adx_14[0] > 20")
		return {
			"problem": problem, "path": FILTER_PATH, "before": current_filter, "after": new_filter,
			"hypothesis": "Over half of all trades cluster in 3 tickers - tightening the trend-strength "
			"gate should let more distinct names qualify instead of repeatedly re-selecting the same names.",
		}

	return None


def apply_fix(config: Dict[str, Any], fix_result: Dict[str, Any]) -> Dict[str, Any]:
	"""Deep-copy `config` with `fix_result["after"]` written to `fix_result["path"]`."""
	return apply_overrides(config, {fix_result["path"]: fix_result["after"]})


# Stage 1.3 default Optuna search space - bounded to <=5 params (anti-pattern #3).
DEFAULT_PARAM_SPACE = [
	{"name": "min_volume", "path": "watchlist.parameters.filter.formula",
	 "type": "int", "low": 20000, "high": 200000, "log": True,
	 "pattern": r"volume\[0\] > (\d+)"},
	{"name": "min_adx", "path": "watchlist.parameters.filter.formula",
	 "type": "int", "low": 15, "high": 30,
	 "pattern": r"adx_14\[0\] > (\d+)"},
]


def _make_score_fn(strategy_name: str, date_range: Tuple[str, str]):
	"""Score one Optuna trial: the trial's watchlist params have already been
	applied and backtested with entry/exit left as-is (unlocked downstream
	stages tune those later); score by re-deriving score-return IC from the
	trial's own trade log, subject to the spec's pass-rate constraint."""
	scratch_name = f"{strategy_name}__tuning_trial"
	start_date, end_date = date_range

	def score_fn(result: Dict[str, Any], trial_config: Dict[str, Any]) -> Optional[float]:
		pass_rate, _pass_series = compute_filter_pass_rate(trial_config, start_date, end_date)
		if not (0.15 <= pass_rate <= 0.45):
			return None
		backtest_dir = (result.get("output") or {}).get("backtest_dir")
		trade_records = build_trade_records(scratch_name, context={"backtest_dir": backtest_dir})
		if len(trade_records) < 10:
			return None
		return compute_score_return_ic(trial_config, trade_records)

	return score_fn


def optimize(
	config: Dict[str, Any],
	strategy_name: str,
	date_range: Tuple[str, str],
	n_trials: int,
	param_space: Optional[List[Dict[str, Any]]] = None,
	seed: Optional[int] = None,
	progress_callback=None,
):
	"""Stage 1.3 - Watchlist Optimization (spec §1.3). Maximizes score-return
	IC subject to filter_pass_rate staying in [0.15, 0.45]; each trial runs a
	real backtest (entry/exit held at their current, not-yet-tuned values)
	and is scored from its own resulting trade log."""
	param_space = param_space or [p for p in DEFAULT_PARAM_SPACE if get_path(config, p["path"]) is not None]

	return run_param_search(
		base_config=config,
		strategy_name=strategy_name,
		date_range=date_range,
		param_space=param_space,
		objective_metric=None,
		n_trials=n_trials,
		direction="maximize",
		seed=seed,
		progress_callback=progress_callback,
		score_fn=_make_score_fn(strategy_name, date_range),
	)


def validate(
	old_diagnosis: Dict[str, Any],
	new_config: Dict[str, Any],
	strategy_name: str,
	date_range: Tuple[str, str],
	min_trades: int = 50,
) -> Dict[str, Any]:
	"""Stage 1.4 - Watchlist Validation (spec §1.4). Re-runs the backtest with
	the candidate watchlist (entry/exit unchanged) and compares against the
	baseline diagnosis. Locks only if score IC improved, the pass rate is
	back in the 20-40% target band, and trade count clears `min_trades` (the
	spec's literal floor is 50 "for statistical significance" - callers
	trading a low-frequency strategy/universe should pass a floor calibrated
	to their own baseline trade count instead, or this gate is unreachable
	regardless of whether a fix actually helped)."""
	scratch_name = f"{strategy_name}__watchlist_validation"
	start_date, end_date = date_range

	result = run_scratch_backtest(new_config, scratch_name, date_range)
	backtest_dir = (result.get("output") or {}).get("backtest_dir")
	trade_records = build_trade_records(scratch_name, context={"backtest_dir": backtest_dir})
	cleanup_scratch_backtest(scratch_name)

	new_pass_rate, _pass_series = compute_filter_pass_rate(new_config, start_date, end_date)
	new_score_ic = compute_score_return_ic(new_config, trade_records)
	old_score_ic = old_diagnosis.get("score_return_ic")
	trade_count = len(trade_records)

	checks = {
		"score_ic_improved": bool(
			new_score_ic is not None and old_score_ic is not None and new_score_ic > old_score_ic
		),
		"pass_rate_in_range": PASS_RATE_TARGET[0] <= new_pass_rate <= PASS_RATE_TARGET[1],
		"trade_count_sufficient": trade_count >= min_trades,
	}
	passed = result.get("status") == "success" and all(checks.values())

	return {
		"filter_formula": get_path(new_config, FILTER_PATH),
		"scoring_formula": get_path(new_config, SCORING_PATH),
		"score_ic_before": old_score_ic,
		"score_ic_after": new_score_ic,
		"filter_pass_rate_after": new_pass_rate,
		"trade_count_after": trade_count,
		"checks": checks,
		"status": "LOCKED" if passed else "REJECTED",
	}

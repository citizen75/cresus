"""Stage 5 — Full Validation (STRATEGY_IMPROVER v2.0 §5).

All upstream stages are locked; this runs final validation on the complete
strategy and decides whether it's safe to ship or overfit and should be
rejected. Per the user's explicit scoping decision, the default is a single
70/30 in-sample/out-of-sample split (one extra backtest) - full rolling
walk-forward analysis and 3-seed parameter-stability re-runs are expensive
(each window/seed is a full backtest) and only run when the caller opts in
via `run_walk_forward` / `run_stability_check`.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from agents.strategy_tuning.common import cleanup_scratch_backtest, run_scratch_backtest

DECAY_RATIO_PASS = 0.6
WALK_FORWARD_STD_STABLE = 0.5
STABILITY_SPREAD_FLAG_PCT = 20.0
OOS_SHARPE_MIN = 0.5  # spec constraint: never recommend a strategy with OOS Sharpe < 0.5


def split_in_sample_out_of_sample(date_range: Tuple[str, str], train_frac: float = 0.7) -> Tuple[Tuple[str, str], Tuple[str, str]]:
	"""Split `date_range` into a leading in-sample slice and a trailing
	out-of-sample slice at `train_frac` of the way through."""
	import pandas as pd

	start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
	split_point = start + (end - start) * train_frac
	is_range = (start.strftime("%Y-%m-%d"), split_point.strftime("%Y-%m-%d"))
	oos_range = ((split_point + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
	return is_range, oos_range


def _run_and_score(config: Dict[str, Any], scratch_name: str, date_range: Tuple[str, str], metric: str = "sharpe_ratio") -> Optional[float]:
	result = run_scratch_backtest(config, scratch_name, date_range)
	cleanup_scratch_backtest(scratch_name)
	if result.get("status") != "success":
		return None
	metrics = (result.get("output") or {}).get("portfolio_metrics") or {}
	return metrics.get(metric)


def run_oos_validation(config: Dict[str, Any], strategy_name: str, date_range: Tuple[str, str]) -> Dict[str, Any]:
	"""Stage 5.1 - In-Sample/Out-of-Sample validation (spec §5.1). The
	already-locked config is run unchanged on both slices (no
	re-optimization per slice - tuning already happened stage by stage on
	the full range; this only checks how much that tuning decays
	out-of-sample)."""
	is_range, oos_range = split_in_sample_out_of_sample(date_range)
	is_sharpe = _run_and_score(config, f"{strategy_name}__oos_is", is_range)
	oos_sharpe = _run_and_score(config, f"{strategy_name}__oos_oos", oos_range)

	decay_ratio = None
	if is_sharpe is not None and oos_sharpe is not None and is_sharpe > 0:
		decay_ratio = oos_sharpe / is_sharpe

	verdict = "OVERFIT"
	if decay_ratio is not None and decay_ratio > DECAY_RATIO_PASS:
		verdict = "PASS"

	return {
		"is_range": is_range, "oos_range": oos_range,
		"is_sharpe": is_sharpe, "oos_sharpe": oos_sharpe,
		"decay_ratio": decay_ratio, "verdict": verdict,
	}


def run_walk_forward(
	config: Dict[str, Any], strategy_name: str, full_range: Tuple[str, str],
	train_months: int = 6, test_months: int = 2,
) -> Dict[str, Any]:
	"""Stage 5.2 - Walk-Forward Analysis (spec §5.2, opt-in via
	`--walk-forward`). Rolls `train_months`-train/`test_months`-test windows
	across `full_range`; the locked config is run unchanged on each test
	window (no per-window re-optimization, for the same reason as 5.1) and
	scored by Sharpe."""
	import pandas as pd

	start, end = pd.Timestamp(full_range[0]), pd.Timestamp(full_range[1])
	window_start = start
	oos_sharpes: List[float] = []

	while True:
		train_end = window_start + pd.DateOffset(months=train_months)
		test_end = train_end + pd.DateOffset(months=test_months)
		if test_end > end:
			break
		test_range = (train_end.strftime("%Y-%m-%d"), test_end.strftime("%Y-%m-%d"))
		sharpe = _run_and_score(config, f"{strategy_name}__wf_{len(oos_sharpes)}", test_range)
		if sharpe is not None:
			oos_sharpes.append(sharpe)
		window_start = window_start + pd.DateOffset(months=test_months)

	if not oos_sharpes:
		return {"windows": 0, "oos_sharpes": [], "mean_oos_sharpe": None, "std_oos_sharpe": None, "verdict": "INSUFFICIENT_DATA"}

	mean_sharpe = sum(oos_sharpes) / len(oos_sharpes)
	variance = sum((s - mean_sharpe) ** 2 for s in oos_sharpes) / len(oos_sharpes)
	std_sharpe = variance ** 0.5

	return {
		"windows": len(oos_sharpes), "oos_sharpes": oos_sharpes,
		"mean_oos_sharpe": mean_sharpe, "std_oos_sharpe": std_sharpe,
		"verdict": "STABLE" if std_sharpe < WALK_FORWARD_STD_STABLE else "UNSTABLE",
	}


def run_parameter_stability(
	optimize_fn: Callable[..., "optuna.Study"],
	config: Dict[str, Any],
	strategy_name: str,
	date_range: Tuple[str, str],
	n_trials: int,
	seeds: Tuple[int, int, int] = (1, 2, 3),
) -> List[Dict[str, Any]]:
	"""Stage 5.3 - Parameter Stability (spec §5.3, opt-in via
	`--check-stability`). Reruns `optimize_fn` (one of the stage modules'
	`optimize()` functions, already bound to its own param_space) 3x with
	different seeds and flags any parameter with > 20% spread across runs."""
	runs = []
	for seed in seeds:
		study = optimize_fn(config, strategy_name, date_range, n_trials, seed=seed)
		runs.append(study.best_trial.params)

	if not runs:
		return []

	results = []
	for name in runs[0].keys():
		values = [run.get(name) for run in runs if name in run]
		if len(values) < len(runs) or not values:
			continue
		mean_value = sum(values) / len(values)
		spread_pct = ((max(values) - min(values)) / mean_value * 100.0) if mean_value else 0.0
		results.append({
			"name": name, "values": values, "spread_pct": spread_pct,
			"verdict": "NOISE" if spread_pct > STABILITY_SPREAD_FLAG_PCT else "STABLE",
		})
	return results


def decide_overfitting(
	oos_result: Dict[str, Any],
	walk_forward_result: Optional[Dict[str, Any]] = None,
	stability_result: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
	"""Stage 5.4 - Overfitting Decision (spec §5.4). REJECT if OOS Sharpe
	decay > 40%, walk-forward std > 0.5, or more than 2 parameters flagged
	NOISE. Also rejects outright if OOS Sharpe itself is below the spec's
	hard floor (constraints: "never recommend a strategy with OOS Sharpe < 0.5"),
	independent of the decay ratio."""
	reasons = []

	decay_ratio = oos_result.get("decay_ratio")
	if decay_ratio is not None and decay_ratio <= (1 - 0.4):
		reasons.append(f"OOS Sharpe decay {(1 - decay_ratio) * 100:.0f}% exceeds the 40% cap")

	oos_sharpe = oos_result.get("oos_sharpe")
	if oos_sharpe is not None and oos_sharpe < OOS_SHARPE_MIN:
		reasons.append(f"OOS Sharpe {oos_sharpe:.2f} is below the {OOS_SHARPE_MIN} floor")

	if walk_forward_result and walk_forward_result.get("std_oos_sharpe") is not None:
		if walk_forward_result["std_oos_sharpe"] > WALK_FORWARD_STD_STABLE:
			reasons.append(f"walk-forward OOS Sharpe std {walk_forward_result['std_oos_sharpe']:.2f} exceeds 0.5")

	noise_count = sum(1 for p in (stability_result or []) if p.get("verdict") == "NOISE")
	if noise_count > 2:
		reasons.append(f"{noise_count} parameters flagged NOISE (> 2 allowed)")

	if not reasons:
		risk = "LOW"
	elif len(reasons) == 1:
		risk = "MEDIUM"
	else:
		risk = "HIGH"

	return {
		"reject": bool(reasons),
		"risk_of_overfitting": risk,
		"reasons": reasons,
	}

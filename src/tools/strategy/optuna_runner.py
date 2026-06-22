"""Generic Optuna parameter search over a strategy config, evaluated by
running real backtests in-process.

Used by every optimizable StrategyTuning stage (watchlist/entry/exit/
portfolio) - each just supplies a different `param_space` (dotted YAML
paths) and `objective_metric` (a key from the backtest's `portfolio_metrics`
dict). One full backtest (~2-4 minutes on the ETF universe) runs per trial,
sequentially - see `n_jobs` note below.
"""

import copy
import re
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import optuna
import yaml

from agents.backtest.agent import BacktestAgent
from tools.strategy.strategy import StrategyManager
from tools.strategy.validator import StrategyValidator

optuna.logging.set_verbosity(optuna.logging.WARNING)

# Penalty score used when a trial violates a constraint or the backtest
# itself errors out - keeps a `best_trial` always selectable instead of
# pruning every bad trial into "no trials available".
_PENALTY = 1e6


def ensure_required_indicators(config: Dict[str, Any]) -> Dict[str, Any]:
	"""Merge every indicator referenced anywhere in `config`'s formulas
	(watchlist, signals, entry, order, exit) into `config["indicators"]`.

	`StrategyAgent` only auto-injects indicators missing from the watchlist
	*filter* formula specifically (a narrow safety net, not a general one).
	A stage fix that edits or removes a clause from one formula can silently
	stop supplying an indicator another, untouched formula still needs (e.g.
	Stage 1 dropping `close[0] > ema_50[0]` from the watchlist filter, while
	Stage 2's entry filter still references `ema_50` - the indicator was
	never declared, just incidentally injected by the clause Stage 1 removed).

	`extract_indicators_from_strategy` regex-extracts every identifier that
	*looks* like an indicator, which also catches names that are only ever
	defined as a named alpha factor under `features.alphas` (e.g.
	`vol_atr_pct`, computed by `WatchlistAlphasAgent`, not by
	`tools.indicators.indicators.calculate()`). Adding one of those to
	`indicators:` makes `calculate()` raise `InvalidFormulaError` for that
	whole batch - silently dropping every *other* indicator requested
	alongside it for that ticker (`DataAgent` catches the exception per
	ticker and just logs a warning), which can zero out an entire backtest's
	trades with no visible error. `check_indicator(..., verbose=False).exists`
	filters those out before they're added.
	Mutates and returns `config`."""
	from tools.indicators import check_indicator

	required = StrategyValidator().extract_indicators_from_strategy(config)
	current = config.get("indicators") or []
	candidates = [ind for ind in sorted(required) if ind not in current]
	if not candidates:
		return config

	results = check_indicator(candidates, verbose=False)
	missing = [ind for ind in candidates if results[ind].exists]
	if missing:
		config["indicators"] = current + missing
	return config


def set_path(config: Dict[str, Any], path: str, value: Any) -> None:
	"""Set `config`'s nested value at dotted `path` (e.g. `"entry.parameters.
	entry_filter.adx_threshold"`), mutating in place. All intermediate keys
	must already exist (tuning only overrides existing leaf parameters)."""
	parts = path.split(".")
	cursor = config
	for part in parts[:-1]:
		if not isinstance(cursor, dict) or part not in cursor:
			raise KeyError(f"Path '{path}' does not exist in config (missing '{part}')")
		cursor = cursor[part]
	cursor[parts[-1]] = value


def get_path(config: Dict[str, Any], path: str) -> Any:
	"""Get `config`'s nested value at dotted `path`, or None if missing."""
	parts = path.split(".")
	cursor: Any = config
	for part in parts:
		if not isinstance(cursor, dict) or part not in cursor:
			return None
		cursor = cursor[part]
	return cursor


def apply_overrides(base_config: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
	"""Deep-copy `base_config` and apply `{dotted_path: value}` overrides."""
	config = copy.deepcopy(base_config)
	for path, value in overrides.items():
		set_path(config, path, value)
	return config


def _suggest(trial: "optuna.Trial", spec: Dict[str, Any]) -> Any:
	"""Sample one raw numeric parameter from an Optuna trial per its spec.

	Spec shape (mirrors the tuning spec's `*_optuna.parameters` entries):
	`{"name": str, "path": str, "type": "int"|"float", "low": num,
	"high": num, "step": Optional[num], "log": Optional[bool], ...}`.
	`path` and any `pattern`/`template` keys are consumed by
	`_resolve_override`, not here.
	"""
	name = spec["name"]
	if spec["type"] == "int":
		return trial.suggest_int(name, spec["low"], spec["high"], step=spec.get("step", 1), log=bool(spec.get("log", False)))
	if spec["type"] == "float":
		return trial.suggest_float(name, spec["low"], spec["high"], step=spec.get("step"), log=bool(spec.get("log", False)))
	raise ValueError(f"Unsupported param type for '{name}': {spec['type']}")


def _resolve_override(base_config: Dict[str, Any], spec: Dict[str, Any], sampled_value: Any) -> Any:
	"""Turn a raw sampled numeric value into whatever should actually be
	written at `spec["path"]`.

	Most leaf strategy parameters are plain formula strings with the tunable
	constant embedded inside an expression (e.g. `"close[0] - atr_14[0] *
	2.0"`), not a bare number - so `set_path` can't just drop the sampled
	value in directly. A spec may supply one of:

	- `pattern`: a regex with one capture group, matched against the
	  *current* string at `path` (read from `base_config`); the captured
	  substring is replaced with the sampled value. Robust across strategies
	  since it edits whatever formula is already there rather than assuming
	  its exact shape.
	- `template`: a `str.format`-style template (e.g.
	  `"close[0] - atr_14[0] * {value}"`) the sampled value is substituted
	  into wholesale, replacing the entire string at `path`.
	- neither: the sampled value is written as-is (the path is already a
	  plain numeric leaf, e.g. `exit.parameters.holding_period.formula`).
	"""
	if "pattern" in spec:
		current = get_path(base_config, spec["path"])
		if not isinstance(current, str):
			raise ValueError(f"'{spec['path']}' is not a string formula; can't apply pattern override for '{spec['name']}'")
		match = re.search(spec["pattern"], current)
		if not match:
			raise ValueError(f"Pattern {spec['pattern']!r} did not match current formula at '{spec['path']}': {current!r}")
		start, end = match.span(1)
		return current[:start] + str(sampled_value) + current[end:]
	if "template" in spec:
		return spec["template"].format(value=sampled_value)
	return sampled_value


def apply_best_trial(base_config: Dict[str, Any], param_space: List[Dict[str, Any]], study: optuna.Study) -> Dict[str, Any]:
	"""Re-apply a completed study's `best_trial.params` to a fresh deep copy
	of `base_config`, using the same `param_space` the study was run with.
	The study itself only records raw sampled values (keyed by `spec["name"]`),
	not the resolved formula strings each trial actually wrote - this
	re-derives them via `_resolve_override` so the winning config can be
	locked in for real, outside the search loop."""
	overrides = {}
	for spec in param_space:
		if spec["name"] not in study.best_trial.params:
			continue
		sampled = study.best_trial.params[spec["name"]]
		overrides[spec["path"]] = _resolve_override(base_config, spec, sampled)
	return apply_overrides(base_config, overrides)


def _extract_metric(result: Dict[str, Any], metric_name: str) -> Optional[float]:
	metrics = (result.get("output") or {}).get("portfolio_metrics") or {}
	value = metrics.get(metric_name)
	if value is None:
		return None
	try:
		return float(value)
	except (TypeError, ValueError):
		return None


def _check_constraints(metrics: Dict[str, Any], constraints: List[Dict[str, Any]]) -> Tuple[bool, str]:
	"""Evaluate `[{"metric": name, "min": x, "max": y}, ...]` against a
	portfolio_metrics dict. Returns (ok, reason)."""
	for c in constraints:
		value = metrics.get(c["metric"])
		if value is None:
			return False, f"constraint metric '{c['metric']}' missing from backtest result"
		value = float(value)
		if "min" in c and value < c["min"]:
			return False, f"{c['metric']}={value:.4f} < min {c['min']}"
		if "max" in c and value > c["max"]:
			return False, f"{c['metric']}={value:.4f} > max {c['max']}"
	return True, ""


def _scratch_strategy_name(strategy_name: str) -> str:
	return f"{strategy_name}__tuning_trial"


def cleanup_scratch_artifacts(strategy_name: str) -> None:
	"""Delete the scratch strategy file and every backtest/portfolio
	directory it accumulated across trials."""
	scratch_name = _scratch_strategy_name(strategy_name)
	manager = StrategyManager()
	scratch_file = manager._get_strategy_file(scratch_name)
	if scratch_file.exists():
		scratch_file.unlink()

	home = Path.home() / ".cresus" / "db"
	for subdir in ("backtests", "portfolios"):
		scratch_dir = home / subdir / scratch_name
		if scratch_dir.exists():
			shutil.rmtree(scratch_dir, ignore_errors=True)


def run_param_search(
	base_config: Dict[str, Any],
	strategy_name: str,
	date_range: Tuple[str, str],
	param_space: List[Dict[str, Any]],
	objective_metric: Optional[str],
	n_trials: int,
	direction: str = "maximize",
	constraints: Optional[List[Dict[str, Any]]] = None,
	seed: Optional[int] = None,
	progress_callback: Optional[Callable[[int, int, float], None]] = None,
	score_fn: Optional[Callable[[Dict[str, Any], Dict[str, Any]], Optional[float]]] = None,
) -> optuna.Study:
	"""Search `param_space` for the value of `objective_metric` that best
	satisfies `direction`, evaluating each candidate with a real backtest.

	Each trial: samples one value per `param_space` entry, applies them to a
	deep copy of `base_config` at the entry's `path`, writes the result to a
	reused scratch strategy file, runs `BacktestAgent` against it over
	`date_range`, and scores the trial from the resulting `portfolio_metrics`.
	Trials that violate `constraints` (or whose backtest errors out) are
	scored with a large penalty rather than pruned, so a usable `best_trial`
	always exists even if every trial fails the constraint.

	Trials run sequentially (`n_jobs=1` is implicit - this function never
	parallelizes). Concurrent `BacktestAgent` runs would race on the same
	scratch portfolio/journal files since each trial reuses one scratch
	strategy name.

	Args:
		base_config: Full current strategy config (already includes any
			upstream stage's locked changes).
		strategy_name: Live strategy name - used to derive the scratch name
			and to label backtest output, not read/written directly.
		date_range: `(start_date, end_date)` strings, `YYYY-MM-DD`.
		param_space: List of parameter specs, see `_suggest`.
		objective_metric: Key to read from `portfolio_metrics` as the score.
			Ignored if `score_fn` is given.
		n_trials: Number of trials to run.
		direction: `"maximize"` or `"minimize"`.
		constraints: Optional list of `{"metric", "min"?, "max"?}` dicts.
		seed: Optional Optuna sampler seed (used by Stage 5's parameter
			stability check, which reruns the same search 3x with different
			seeds).
		progress_callback: Optional `(trial_number, n_trials, score) -> None`
			invoked after each trial, e.g. for CLI progress output.
		score_fn: Optional `(backtest_result, trial_config) -> Optional[float]`
			to score a trial from something other than `portfolio_metrics`
			(e.g. Stage 1's score-return IC, computed from the trial's trade
			log + watchlist scoring formula). Takes precedence over
			`objective_metric` when given; returning `None` scores the trial
			as a constraint-style penalty.

	Returns:
		The completed `optuna.Study`. `study.best_trial.params` holds the
		best raw param values (keyed by each spec's `name`); re-apply them
		via `apply_overrides` using each spec's `path` to get the winning
		config.
	"""
	scratch_name = _scratch_strategy_name(strategy_name)
	manager = StrategyManager()
	start_date, end_date = date_range

	def objective(trial: "optuna.Trial") -> float:
		overrides = {}
		for spec in param_space:
			sampled = _suggest(trial, spec)
			overrides[spec["path"]] = _resolve_override(base_config, spec, sampled)

		trial_config = apply_overrides(base_config, overrides)
		trial_config["name"] = scratch_name
		ensure_required_indicators(trial_config)

		scratch_file = manager._get_strategy_file(scratch_name)
		manager._ensure_strategies_dir()
		with open(scratch_file, "w") as f:
			yaml.dump(trial_config, f, default_flow_style=False, sort_keys=False)

		penalty = _PENALTY if direction == "maximize" else -_PENALTY

		try:
			result = BacktestAgent().process({
				"strategy_name": scratch_name,
				"start_date": start_date,
				"end_date": end_date,
			})
		except Exception:
			if progress_callback:
				progress_callback(trial.number, n_trials, penalty)
			return penalty

		if result.get("status") != "success":
			if progress_callback:
				progress_callback(trial.number, n_trials, penalty)
			return penalty

		metrics = (result.get("output") or {}).get("portfolio_metrics") or {}
		if constraints:
			ok, _reason = _check_constraints(metrics, constraints)
			if not ok:
				if progress_callback:
					progress_callback(trial.number, n_trials, penalty)
				return penalty

		score = score_fn(result, trial_config) if score_fn else _extract_metric(result, objective_metric)
		if score is None:
			if progress_callback:
				progress_callback(trial.number, n_trials, penalty)
			return penalty

		if progress_callback:
			progress_callback(trial.number, n_trials, score)
		return score

	sampler = optuna.samplers.TPESampler(seed=seed) if seed is not None else None
	study = optuna.create_study(direction=direction, sampler=sampler)
	study.optimize(objective, n_trials=n_trials)

	cleanup_scratch_artifacts(strategy_name)
	return study

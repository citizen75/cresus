"""Shared scratch-backtest machinery for every StrategyTuning stage.

Each stage (watchlist/entry/exit/portfolio) needs to run disposable, real
backtests against trial configs - to build a full `data_history` for cheap
formula replays, or to validate a candidate fix - without ever touching the
live strategy file. These helpers centralize that lifecycle: write a scratch
strategy file, run the real prep pipeline or a full backtest, then clean up.
"""

import shutil
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml

from agents.backtest.agent import BacktestAgent
from agents.data.agent import DataAgent
from agents.strategy.agent import StrategyAgent
from agents.watchlist_alphas.agent import WatchlistAlphasAgent
from core.context import AgentContext
from tools.strategy.optuna_runner import ensure_required_indicators
from tools.strategy.strategy import StrategyManager


def write_scratch_strategy(config: Dict[str, Any], scratch_name: str) -> Path:
	"""Write `config` (with every formula's required indicators merged in -
	see `ensure_required_indicators`) to a scratch strategy file named
	`scratch_name`, overwriting any previous scratch file of that name."""
	manager = StrategyManager()
	trial_config = dict(config)
	trial_config["name"] = scratch_name
	ensure_required_indicators(trial_config)
	scratch_file = manager._get_strategy_file(scratch_name)
	manager._ensure_strategies_dir()
	with open(scratch_file, "w") as f:
		yaml.dump(trial_config, f, default_flow_style=False, sort_keys=False)
	return scratch_file


def prepare_data_history(config: Dict[str, Any], scratch_name: str) -> Dict[str, Any]:
	"""Build the same `{ticker: DataFrame}` data_history a real backtest
	would see - full cached OHLCV plus every indicator and alpha column the
	strategy's formulas reference - by running the exact prep agents
	`BacktestAgent` itself runs (`StrategyAgent` -> `DataAgent` ->
	`WatchlistAlphasAgent`), minus the order/portfolio simulation.

	No backtest/portfolio directories are created since `BacktestAgent`
	itself never runs here - only the scratch strategy file needs cleanup."""
	scratch_file = write_scratch_strategy(config, scratch_name)
	try:
		context = AgentContext()
		strategy_result = StrategyAgent(f"strategy[{scratch_name}]", context).run({})
		if strategy_result.get("status") == "error":
			return {}
		data_result = DataAgent(f"data[{scratch_name}]", context).run({})
		if data_result.get("status") == "error":
			return {}
		WatchlistAlphasAgent(f"alphas[{scratch_name}]", context).run({})
		return context.get("data_history") or {}
	finally:
		if scratch_file.exists():
			scratch_file.unlink()


def run_scratch_backtest(config: Dict[str, Any], scratch_name: str, date_range: Tuple[str, str]) -> Dict[str, Any]:
	"""Write `config` to a disposable scratch strategy file and run one
	backtest over `date_range`. Returns the raw `BacktestAgent().process()`
	result dict.

	Does NOT clean up the backtest/portfolio output - the caller still needs
	to read the trade log out of it (e.g. via `build_trade_records`) before
	those artifacts can go away. Call `cleanup_scratch_backtest` once that's
	done. Only the scratch strategy file itself (no longer needed once the
	backtest has started) is removed here."""
	scratch_file = write_scratch_strategy(config, scratch_name)
	start_date, end_date = date_range
	try:
		return BacktestAgent().process({
			"strategy_name": scratch_name,
			"start_date": start_date,
			"end_date": end_date,
		})
	finally:
		if scratch_file.exists():
			scratch_file.unlink()


def cleanup_scratch_backtest(scratch_name: str) -> None:
	"""Delete the backtest/portfolio directories `run_scratch_backtest` left
	behind for `scratch_name`, once the caller is done reading from them."""
	home = Path.home() / ".cresus" / "db"
	for subdir in ("backtests", "portfolios"):
		scratch_dir = home / subdir / scratch_name
		if scratch_dir.exists():
			shutil.rmtree(scratch_dir, ignore_errors=True)

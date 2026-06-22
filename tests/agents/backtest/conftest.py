"""Shared fixtures/helpers for BacktestAgent tests.

Builds a real backtest context from init/templates/strategy.yml, restricted to the
AAPL fixture only (tests/fixtures/data/AAPL.parquet) so runs are deterministic and
don't need network/universe lookups.
"""

import shutil
import sys
import uuid
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from agents.backtest.agent import BacktestAgent
from core.context import AgentContext
from tools.indicators.indicators import calculate as calculate_indicators, register_indicators_for_formulas
from tools.strategy.alphas import merge_shared_alphas
from utils.env import get_db_root

TEMPLATE_STRATEGY_PATH = Path(__file__).parent.parent.parent.parent / "init" / "templates" / "strategy.yml"


def load_template_strategy_config() -> dict:
    """Load init/templates/strategy.yml, restricted to run standalone against AAPL only:
    drop "universe" and set "tickers": ["AAPL"] so StrategyAgent doesn't need a real
    universe file lookup. The template opts into the shared alphas catalog via
    features.shared_alphas, so merge it in here too since tests load the YAML
    directly instead of going through StrategyManager.load_strategy()."""
    with open(TEMPLATE_STRATEGY_PATH) as f:
        config = yaml.safe_load(f)
    config.pop("universe", None)
    config["tickers"] = ["AAPL"]
    merge_shared_alphas(config)
    return config


def load_aapl_data_with_indicators(test_data_dir: Path, indicators: list) -> Dict[str, pd.DataFrame]:
    """Load the AAPL fixture and pre-compute indicator columns exactly like DataAgent
    does for freshly-fetched data, since DataAgent skips recalculation when
    data_history is already in context (see agents/data/agent.py:138)."""
    register_indicators_for_formulas(indicators)

    df = pd.read_parquet(test_data_dir / "AAPL.parquet")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df_asc = df.sort_values("timestamp", ascending=True).reset_index(drop=True)

    calculated = calculate_indicators(indicators, df_asc)
    for name, series in calculated.items():
        df_asc[name] = series

    return {"AAPL": df_asc.sort_values("timestamp", ascending=False).reset_index(drop=True)}


def build_backtest_context(test_data_dir: Path, portfolio_name: str) -> AgentContext:
    """Build a fresh context seeded with the template strategy config (AAPL-only) and
    pre-computed AAPL data, so StrategyAgent/DataAgent skip network/StrategyManager
    lookups and use this fixture data directly."""
    strategy_config = load_template_strategy_config()
    data_history = load_aapl_data_with_indicators(test_data_dir, strategy_config["indicators"])

    context = AgentContext()
    context.set("strategy_config", strategy_config)
    context.set("data_history", data_history)
    context.set("tickers", ["AAPL"])
    context.set("portfolio_name", portfolio_name)
    return context


def cleanup_portfolio_and_backtests(portfolio_name: str, strategy_name: str) -> None:
    db_root = get_db_root()
    shutil.rmtree(db_root / "portfolios" / portfolio_name, ignore_errors=True)
    shutil.rmtree(db_root / "backtests" / strategy_name, ignore_errors=True)


@pytest.fixture
def isolated_name():
    """A unique portfolio/strategy name per test, cleaned up on disk afterward."""
    name = f"test_backtest_{uuid.uuid4().hex[:8]}"
    yield name
    cleanup_portfolio_and_backtests(name, name)


def run_backtest(
    test_data_dir: Path,
    name: str,
    start_date: str = "2025-06-01",
    end_date: str = "2026-02-05",
) -> Tuple[BacktestAgent, dict]:
    """Run a real BacktestAgent against the AAPL-only template strategy context.

    This date range (~172 trading days) is wide enough for the template's 200/250-day
    indicators (sma_200, roc_250) to have warmed up and for real entries/exits to occur.
    """
    context = build_backtest_context(test_data_dir, name)
    agent = BacktestAgent(websocket=False, context=context)
    result = agent.process({
        "strategy_name": name,
        "portfolio_name": name,
        "start_date": start_date,
        "end_date": end_date,
    })
    return agent, result


@pytest.fixture(scope="module")
def template_backtest_run():
    """Run one real backtest (template strategy, AAPL-only) shared across a module's
    test methods that only inspect different facets of the same deterministic run.

    Module-scoped, so it can't depend on the function-scoped `test_data_dir` fixture -
    the fixtures dir path is fixed relative to this file anyway.
    """
    data_dir = Path(__file__).parent.parent.parent / "fixtures" / "data"
    name = f"test_backtest_module_{uuid.uuid4().hex[:8]}"
    agent, result = run_backtest(data_dir, name)
    yield agent, result, name
    cleanup_portfolio_and_backtests(name, name)

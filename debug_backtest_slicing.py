#!/usr/bin/env python3
"""Debug script to test BacktestAgent's data slicing on premarket."""

import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.context import AgentContext
from flows.premarket import PreMarketFlow
from agents.backtest.agent import BacktestAgent

def test_backtest_slicing():
    """Simulate BacktestAgent's _set_data_history_for_date and run premarket."""
    print(f"\n{'='*80}")
    print("TEST: BacktestAgent data slicing on 2026-05-07")
    print(f"{'='*80}")

    # Create context and load data like BacktestAgent does
    context = AgentContext()
    context.set("backtest_id", "debug")

    # Load data via DataAgent (full range)
    from agents.data.agent import DataAgent
    data_agent = DataAgent("DataAgent", context=context)
    data_result = data_agent.run({
        "tickers": ["DE0005933972", "LU0274211480", "IE00BG143G97", "FR0010468983",
                   "LU2082996385", "LU0380865021"]  # Tickers that passed in backtest
    })

    print(f"\nData loaded: {data_result.get('status')}")
    data_history_full = context.get("data_history") or {}
    print(f"Full data_history: {len(data_history_full)} tickers")

    # Now slice to 2026-05-07 like BacktestAgent does
    print(f"\nSlicing data to 2026-05-07...")
    target_date = date.fromisoformat("2026-05-07")

    import pandas as pd
    sliced_history = {}
    for ticker, df in data_history_full.items():
        if df.empty:
            sliced_history[ticker] = df
            continue

        if "timestamp" in df.columns:
            timestamps = pd.to_datetime(df["timestamp"])
        else:
            timestamps = pd.to_datetime(df.index)

        dates = timestamps.dt.date
        mask = dates <= target_date
        sliced_history[ticker] = df[mask].copy()
        print(f"  {ticker}: {len(df)} rows -> {len(sliced_history[ticker])} rows after slicing")

    # Set sliced data in context
    context.set("data_history", sliced_history)

    # Now run premarket with sliced data
    print(f"\nRunning premarket with SLICED data (backtest mode)...")
    flow = PreMarketFlow("etf_pea_trend", context=context)
    result = flow.process({"date": "2026-05-07"})

    watchlist = context.get("watchlist") or []
    print(f"Watchlist after slicing: {len(watchlist)} tickers")
    print(f"Watchlist: {watchlist}")

    # Check entry recommendations
    entry_step = flow.get_step("entry")
    if entry_step:
        entry_result = entry_step.get("result")
        if entry_result and entry_result.get("status") == "success":
            output = entry_result.get("output", {})
            top_ops = output.get("top_opportunities", [])
            print(f"Entry recommendations: {len(top_ops)}")
            for rec in top_ops:
                print(f"  {rec.get('ticker')}")

    return result


if __name__ == "__main__":
    result = test_backtest_slicing()
    print(f"\n{'='*80}")
    print(f"Result: {result.get('status')}")

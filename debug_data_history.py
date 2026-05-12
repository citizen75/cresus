#!/usr/bin/env python3
"""Debug script to compare data_history between backtest and premarket execution."""

import sys
from pathlib import Path
import json
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.context import AgentContext
from flows.premarket import PreMarketFlow
from flows.backtest import BacktestFlow

def capture_data_history_at_entry(context, label):
    """Capture data_history state at entry step."""
    data_history = context.get("data_history") or {}

    print(f"\n{'='*80}")
    print(f"DATA HISTORY SNAPSHOT: {label}")
    print(f"{'='*80}")
    print(f"Total tickers: {len(data_history)}")

    # Get first ticker for detailed analysis
    if data_history:
        first_ticker = list(data_history.keys())[0]
        df = data_history[first_ticker]

        print(f"\nFirst ticker: {first_ticker}")
        print(f"  Rows: {len(df)}")
        print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"  Columns: {list(df.columns)}")

        # Show first 5 rows
        print(f"\n  First 5 rows (descending order - most recent first):")
        for idx, row in df.head(5).iterrows():
            sha_green = row.get('sha_10_green', 'N/A')
            sha_red = row.get('sha_10_red', 'N/A')
            adx_14 = row.get('adx_14', 'N/A')
            ts = row.get('timestamp', 'N/A')
            print(f"    [{idx}] {ts} | sha_10_green={sha_green} | sha_10_red={sha_red} | adx_14={adx_14}")

    # Check indicator presence across all tickers
    indicator_presence = {}
    for ticker, df in data_history.items():
        for col in ['sha_10_green', 'sha_10_red', 'adx_14']:
            if col not in indicator_presence:
                indicator_presence[col] = {'present': 0, 'missing': 0}
            if col in df.columns:
                indicator_presence[col]['present'] += 1
            else:
                indicator_presence[col]['missing'] += 1

    print(f"\n  Indicator presence across {len(data_history)} tickers:")
    for ind, counts in indicator_presence.items():
        print(f"    {ind}: {counts['present']}/{len(data_history)} present")

    return data_history


def test_single_premarket():
    """Run premarket for 2026-05-07 and capture data_history."""
    print("\n" + "="*80)
    print("RUNNING SINGLE PREMARKET: 2026-05-07")
    print("="*80)

    context = AgentContext()
    flow = PreMarketFlow("etf_pea_trend", context=context)

    # Run premarket
    result = flow.process({"date": "2026-05-07"})

    # Capture data after data agent but before entry
    # We'll need to check at entry step
    data_history = capture_data_history_at_entry(context, "PREMARKET (2026-05-07) - After Data Agent")

    print(f"\nPremarket result:")
    print(f"  Status: {result.get('status')}")
    print(f"  Watchlist count: {result.get('count')}")
    print(f"  Entry recommendations: {len(result.get('entry_recommendations', []))}")
    print(f"  Orders: {result.get('orders_count', 0)}")

    return data_history


def test_backtest():
    """Run backtest for 2026-05-01 and capture data for 2026-05-07."""
    print("\n" + "="*80)
    print("RUNNING BACKTEST: 2026-05-01 (will process 2026-05-07 as part of range)")
    print("="*80)

    # We need to hook into the backtest to capture data for 2026-05-07
    # This is tricky - we need to run backtest and intercept the premarket call

    # For now, let's check what date the backtest actually processes
    # by looking at the recent backtest output

    context = AgentContext()

    # Instead of running full backtest, let's manually run premarket with backtest context
    context.set("backtest_id", "debug")  # Set backtest mode

    flow = PreMarketFlow("etf_pea_trend", context=context)

    # Run premarket with backtest context for 2026-05-07
    result = flow.process({"date": "2026-05-07"})

    data_history = capture_data_history_at_entry(context, "BACKTEST-MODE (2026-05-07) - After Data Agent")

    print(f"\nBacktest-mode premarket result:")
    print(f"  Status: {result.get('status')}")
    print(f"  Watchlist count: {result.get('count')}")
    print(f"  Entry recommendations: {len(result.get('entry_recommendations', []))}")
    print(f"  Orders: {result.get('orders_count', 0)}")

    return data_history


def compare_data_histories():
    """Compare data_history between backtest and premarket."""
    print("\n\n" + "="*80)
    print("COMPARING DATA HISTORIES")
    print("="*80)

    # Run both
    pm_data = test_single_premarket()
    bm_data = test_backtest()

    # Compare
    print(f"\n{'='*80}")
    print("COMPARISON")
    print(f"{'='*80}")

    print(f"\nPremarket tickers: {len(pm_data)}")
    print(f"Backtest tickers: {len(bm_data)}")

    # Check if same tickers loaded
    pm_tickers = set(pm_data.keys())
    bm_tickers = set(bm_data.keys())

    only_in_pm = pm_tickers - bm_tickers
    only_in_bm = bm_tickers - pm_tickers

    if only_in_pm:
        print(f"\nTickers only in premarket: {only_in_pm}")
    if only_in_bm:
        print(f"Tickers only in backtest: {only_in_bm}")

    if pm_tickers == bm_tickers:
        print("\n✓ Same tickers loaded in both flows")
    else:
        print(f"\n✗ Different tickers! PM has {len(only_in_pm)} extra, BM has {len(only_in_bm)} extra")

    # Compare data for a few key tickers that passed in backtest
    backtest_tickers = ["FR0010468983", "LU2082996385", "LU0380865021"]

    print(f"\n{'='*80}")
    print("DETAILED COMPARISON FOR BACKTEST-PASSING TICKERS")
    print(f"{'='*80}")

    for ticker in backtest_tickers:
        if ticker in pm_data and ticker in bm_data:
            pm_df = pm_data[ticker]
            bm_df = bm_data[ticker]

            print(f"\n{ticker}:")
            print(f"  Premarket rows: {len(pm_df)}")
            print(f"  Backtest rows: {len(bm_df)}")

            # Compare first 5 rows
            if len(pm_df) > 0 and len(bm_df) > 0:
                print(f"  Premarket first row: {pm_df.iloc[0]['timestamp']} - sha_10_green={pm_df.iloc[0].get('sha_10_green')} sha_10_red={pm_df.iloc[0].get('sha_10_red')} adx_14={pm_df.iloc[0].get('adx_14')}")
                print(f"  Backtest first row:  {bm_df.iloc[0]['timestamp']} - sha_10_green={bm_df.iloc[0].get('sha_10_green')} sha_10_red={bm_df.iloc[0].get('sha_10_red')} adx_14={bm_df.iloc[0].get('adx_14')}")


if __name__ == "__main__":
    compare_data_histories()

#!/usr/bin/env python3
"""Debug script to trace watchlist and entry filtering."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.context import AgentContext
from flows.premarket import PreMarketFlow

def trace_flow_for_date(date_str, backtest_mode=False):
    """Run flow and trace watchlist through entry step."""
    label = "BACKTEST" if backtest_mode else "PREMARKET"
    print(f"\n{'='*80}")
    print(f"{label} MODE FOR {date_str}")
    print(f"{'='*80}")

    context = AgentContext()
    if backtest_mode:
        context.set("backtest_id", "debug")

    flow = PreMarketFlow("etf_pea_trend", context=context)

    # Run flow
    result = flow.process({"date": date_str})

    # Get intermediate results
    data_history = context.get("data_history") or {}
    watchlist = context.get("watchlist") or []
    ticker_scores = context.get("ticker_scores") or {}
    signals = context.get("signals") or {}

    print(f"\nData tickers loaded: {len(data_history)}")
    print(f"Watchlist size after watchlist step: {len(watchlist)}")
    print(f"Watchlist tickers: {watchlist}")

    # Get entry results
    entry_step = flow.get_step("entry")
    if entry_step:
        entry_result = entry_step.get("result")
        if entry_result and entry_result.get("status") == "success":
            output = entry_result.get("output", {})
            top_ops = output.get("top_opportunities", [])
            print(f"\nEntry recommendations: {len(top_ops)}")
            for rec in top_ops[:10]:
                print(f"  {rec.get('ticker')}: score={rec.get('entry_score')}")

    # Get entry_order results
    entry_order_step = flow.get_step("entry_order")
    if entry_order_step:
        eo_result = entry_order_step.get("result")
        if eo_result and eo_result.get("status") == "success":
            output = eo_result.get("output", {})
            orders = output.get("orders", [])
            print(f"\nFinal orders: {len(orders)}")
            for order in orders:
                print(f"  {order.get('ticker')}")

    return {
        'date': date_str,
        'mode': label,
        'data_tickers': len(data_history),
        'watchlist_size': len(watchlist),
        'watchlist': watchlist,
        'orders': len(result.get('executable_orders', [])) if result.get('executable_orders') else 0,
    }


if __name__ == "__main__":
    # Test both modes for 2026-05-07
    pm_result = trace_flow_for_date("2026-05-07", backtest_mode=False)
    bm_result = trace_flow_for_date("2026-05-07", backtest_mode=True)

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Premarket watchlist: {pm_result['watchlist_size']} tickers")
    print(f"Backtest watchlist: {bm_result['watchlist_size']} tickers")
    print(f"Premarket orders: {pm_result['orders']}")
    print(f"Backtest orders: {bm_result['orders']}")

    # Check which tickers are in watchlist for each
    print(f"\nBacktest watchlist tickers: {bm_result['watchlist']}")

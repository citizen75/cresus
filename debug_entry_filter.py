#!/usr/bin/env python3
"""Debug entry_filter evaluation for specific tickers."""

import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.context import AgentContext
from agents.entry.sub_agents import EntryFilterAgent
from agents.data.agent import DataAgent

def test_entry_filter_on_tickers():
    """Test entry_filter formula on the tickers that passed in backtest."""
    print(f"\n{'='*80}")
    print("TEST: Entry filter evaluation on backtest-passing tickers")
    print(f"{'='*80}")

    # Tickers that generated orders in backtest on 2026-05-07
    test_tickers = ["FR0010468983", "LU2082996385", "LU0380865021"]

    # Load data for these tickers
    context = AgentContext()
    context.set("backtest_id", "debug")

    data_agent = DataAgent("DataAgent", context=context)
    data_result = data_agent.run({"tickers": test_tickers})

    print(f"\nData loaded: {data_result.get('status')}")
    data_history = context.get("data_history") or {}
    print(f"Tickers in data_history: {list(data_history.keys())}")

    # Load strategy to get entry_filter formula
    from tools.strategy import StrategyManager
    sm = StrategyManager()
    strategy_result = sm.load_strategy("etf_pea_trend")
    if strategy_result.get("status") == "success":
        strategy_config = strategy_result.get("data", {})
        context.set("strategy_config", strategy_config)

        # Get entry_filter formula
        entry_filter = strategy_config.get("entry_filter", "")
        print(f"\nEntry filter formula:")
        print(f"  {entry_filter}")

        # Create mock entry recommendations (tickers are in watchlist but haven't been scored)
        entry_recommendations = []
        for ticker in test_tickers:
            entry_recommendations.append({
                "ticker": ticker,
                "entry_score": 100,  # Mock score
                "recommendation": "BUY",
                "timestamp": "2026-05-07T09:00:00"
            })

        context.set("entry_recommendations", entry_recommendations)
        print(f"\nEntry recommendations (before filter): {len(entry_recommendations)} tickers")
        for rec in entry_recommendations:
            print(f"  {rec['ticker']}: score={rec['entry_score']}")

        # Run entry_filter agent
        entry_filter_agent = EntryFilterAgent("EntryFilterAgent")
        entry_filter_agent.context = context
        filter_result = entry_filter_agent.process()

        print(f"\nEntry filter result: {filter_result.get('status')}")
        if filter_result.get("status") == "success":
            filtered = filter_result.get("output", {}).get("filtered_recommendations", [])
            print(f"Entry recommendations (after filter): {len(filtered)} tickers")
            for rec in filtered:
                print(f"  {rec['ticker']}: score={rec['entry_score']}")

            # Check why some were filtered out
            if len(filtered) < len(entry_recommendations):
                print(f"\n{len(entry_recommendations) - len(filtered)} tickers were filtered out")

                # Let's manually check the formula on each ticker
                print(f"\nManual formula evaluation:")
                for ticker in test_tickers:
                    if ticker in data_history:
                        df = data_history[ticker]
                        if len(df) > 0:
                            print(f"\n  {ticker}:")
                            print(f"    Rows: {len(df)}")
                            print(f"    First 5 rows (newest first):")
                            for idx in range(min(5, len(df))):
                                row = df.iloc[idx]
                                ts = row.get('timestamp', 'N/A')
                                sha_g = row.get('sha_10_green', 'N/A')
                                sha_r = row.get('sha_10_red', 'N/A')
                                adx = row.get('adx_14', 'N/A')
                                print(f"      [{idx}] {ts} | green={sha_g} red={sha_r} adx={adx}")

                            # Test formula conditions
                            if len(df) >= 3:
                                row_0 = df.iloc[0]  # Most recent (index 0)
                                row_1 = df.iloc[1]  # Second most recent (index -1)
                                row_2 = df.iloc[2]  # Third most recent (index -2)

                                print(f"\n    Formula check:")
                                cond_1 = row_0.get('sha_10_green', 0) == 1
                                cond_2 = row_1.get('sha_10_green', 0) == 1
                                cond_3 = row_2.get('sha_10_red', 0) == 1
                                cond_4 = (row_0.get('adx_14', 0) or 0) > 25

                                print(f"      sha_10_green[0]==1: {cond_1}")
                                print(f"      sha_10_green[-1]==1: {cond_2}")
                                print(f"      sha_10_red[-2]==1: {cond_3}")
                                print(f"      adx_14[0]>25: {cond_4}")
                                print(f"      ALL: {cond_1 and cond_2 and cond_3 and cond_4}")


if __name__ == "__main__":
    test_entry_filter_on_tickers()

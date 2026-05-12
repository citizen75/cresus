#!/usr/bin/env python3
"""Debug why indicators aren't calculated when loading 3 tickers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.context import AgentContext
from agents.data.agent import DataAgent
from tools.strategy import StrategyManager

def test_indicators_with_config():
    """Load strategy config first, then load data."""
    print(f"\n{'='*80}")
    print("TEST: Load strategy config BEFORE DataAgent")
    print(f"{'='*80}")

    context = AgentContext()

    # Load strategy config first
    sm = StrategyManager()
    strategy_result = sm.load_strategy("etf_pea_trend")
    if strategy_result.get("status") == "success":
        strategy_config = strategy_result.get("data", {})
        context.set("strategy_config", strategy_config)

        # Get indicators from config
        indicators = strategy_config.get("indicators", [])
        print(f"\nIndicators from config: {indicators}")
        context.set("indicators", indicators)  # Store in context too

    # Now load data with strategy config in context
    test_tickers = ["FR0010468983", "LU2082996385", "LU0380865021"]
    data_agent = DataAgent("DataAgent", context=context)
    data_result = data_agent.run({"tickers": test_tickers})

    print(f"\nData loaded: {data_result.get('status')}")
    data_history = context.get("data_history") or {}

    # Check if indicators are now present
    for ticker in test_tickers:
        if ticker in data_history:
            df = data_history[ticker]
            print(f"\n{ticker}:")
            print(f"  Rows: {len(df)}")
            print(f"  Columns: {list(df.columns)}")

            # Check for specific indicators
            has_sha_green = 'sha_10_green' in df.columns
            has_sha_red = 'sha_10_red' in df.columns
            has_adx = 'adx_14' in df.columns

            print(f"  Has sha_10_green: {has_sha_green}")
            print(f"  Has sha_10_red: {has_sha_red}")
            print(f"  Has adx_14: {has_adx}")

            if has_sha_green and len(df) > 0:
                print(f"  sha_10_green[0]: {df.iloc[0].get('sha_10_green', 'N/A')}")
                print(f"  sha_10_red[0]: {df.iloc[0].get('sha_10_red', 'N/A')}")
                print(f"  adx_14[0]: {df.iloc[0].get('adx_14', 'N/A')}")


if __name__ == "__main__":
    test_indicators_with_config()

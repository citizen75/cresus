#!/usr/bin/env python3
"""Test 10 HAMA entry formulas for CAC40."""

import subprocess
import yaml
import json
from pathlib import Path
from datetime import datetime
import time
import pandas as pd

# 10 HAMA entry formulas
FORMULAS = [
    {
        "name": "Formula 1 (Simple Green)",
        "formula": "hama_25_20_55_green[0]==1"
    },
    {
        "name": "Formula 2 (Green + Above Trend)",
        "formula": "hama_25_20_55_green[0]==1 && close[0] > hama_25_20_55_trend[0]"
    },
    {
        "name": "Formula 3 (Triple Green)",
        "formula": "hama_25_20_55_green[0]==1 && hama_25_20_55_green[-1]==1 && hama_25_20_55_green[-2]==1"
    },
    {
        "name": "Formula 4 (Strong Candle Body)",
        "formula": "hama_25_20_55_green[0]==1 && (hama_25_20_55_close[0] - hama_25_20_55_open[0]) / hama_25_20_55_open[0] > 0.01"
    },
    {
        "name": "Formula 5 (Bullish Trend Cross)",
        "formula": "hama_25_20_55_green[0]==1 && close[0] > hama_25_20_55_trend[0] && close[-1] < hama_25_20_55_trend[-1]"
    },
    {
        "name": "Formula 6 (Wide Body Momentum)",
        "formula": "hama_25_20_55_green[0]==1 && (hama_25_20_55_close[0] - hama_25_20_55_open[0]) > (hama_25_20_55_high[0] - hama_25_20_55_low[0]) * 0.6"
    },
    {
        "name": "Formula 7 (Trend Strength)",
        "formula": "hama_25_20_55_green[0]==1 && hama_25_20_55_trend[0] > sma_50[0] && close[0] > hama_25_20_55_trend[0]"
    },
    {
        "name": "Formula 8 (Double Green + Volume)",
        "formula": "hama_25_20_55_green[-1]==1 && hama_25_20_55_green[0]==1 && volume[0] > volume_sma_20[0] * 1.1"
    },
    {
        "name": "Formula 9 (RSI Oversold Bounce)",
        "formula": "hama_25_20_55_green[0]==1 && rsi_7[-1] < 35 && rsi_7[0] > 35 && close[0] > hama_25_20_55_trend[0]"
    },
    {
        "name": "Formula 10 (Support Break)",
        "formula": "hama_25_20_55_green[0]==1 && close[0] >= hama_25_20_55_low[0] && close[0] < hama_25_20_55_low[0] * 1.02 && close[0] > ema_50[0]"
    }
]

STRATEGY_PATH = Path.home() / ".cresus/db/strategies/cac_trend_hama.yml"
BACKTEST_PATH = Path.home() / ".cresus/db/backtests/cac_trend_hama"
START_DATE = "2025-01-01"
END_DATE = "2026-01-01"


def load_strategy():
    """Load strategy YAML."""
    with open(STRATEGY_PATH, 'r') as f:
        return yaml.safe_load(f)


def save_strategy(strategy_data):
    """Save strategy YAML."""
    with open(STRATEGY_PATH, 'w') as f:
        yaml.safe_dump(strategy_data, f, default_flow_style=False, sort_keys=False)


def run_backtest():
    """Run backtest command."""
    cmd = ["cresus", "backtest", "run", "cac_trend_hama", START_DATE, END_DATE]
    print(f"  Running: cresus backtest run cac_trend_hama {START_DATE} {END_DATE}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return True
    except subprocess.TimeoutExpired:
        print("    ⚠️  Backtest timed out (180s)")
        return False
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False


def extract_metrics_from_json():
    """Extract metrics from the most recent backtest JSON."""
    if not BACKTEST_PATH.exists():
        return None, None

    try:
        latest = max(BACKTEST_PATH.glob("*/metrics.json"), key=lambda p: p.parent.stat().st_mtime)
        with open(latest, 'r') as f:
            metrics = json.load(f)

        total_return = metrics.get("total_return_pct")
        num_trades = metrics.get("total_trades", 0)

        return total_return, num_trades
    except Exception as e:
        print(f"    ❌ Error extracting metrics: {e}")
        return None, None


def main():
    """Test all HAMA formulas."""
    print(f"\n{'='*90}")
    print(f"Testing 10 HAMA Entry Formulas for CAC40")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"{'='*90}\n")

    results = []

    for i, formula_config in enumerate(FORMULAS, 1):
        print(f"[{i}/10] {formula_config['name']}")
        print(f"  Formula: {formula_config['formula'][:70]}...")

        # Load strategy and update entry formula
        strategy = load_strategy()
        strategy['entry']['parameters']['entry_filter']['formula'] = formula_config['formula']
        save_strategy(strategy)

        # Run backtest
        if not run_backtest():
            results.append({
                "num": i,
                "name": formula_config['name'],
                "formula": formula_config['formula'],
                "return": None,
                "trades": None,
                "status": "❌"
            })
            print("  Failed to run backtest\n")
            continue

        # Small delay to ensure file is written
        time.sleep(2)

        # Extract metrics
        return_pct, num_trades = extract_metrics_from_json()

        if return_pct is not None:
            status = "✅"
        else:
            status = "❌"

        result = {
            "num": i,
            "name": formula_config['name'],
            "formula": formula_config['formula'],
            "return": return_pct,
            "trades": num_trades,
            "status": status
        }
        results.append(result)

        ret_str = f"{return_pct:+.2f}%" if return_pct is not None else "N/A"
        trades_str = f"{num_trades}" if num_trades is not None else "N/A"
        print(f"  {status} Return: {ret_str}, Trades: {trades_str}\n")

    # Print summary table
    print(f"{'='*90}")
    print("RESULTS SUMMARY - HAMA FORMULAS")
    print(f"{'='*90}\n")

    print(f"{'#':<3} {'Formula Name':<25} {'Return':<12} | {'Trades':<8}")
    print(f"{'-'*85}")

    for r in sorted(results, key=lambda x: x['return'] if x['return'] is not None else float('-inf'), reverse=True):
        ret_str = f"{r['return']:+.2f}%" if r['return'] is not None else "N/A"
        trades_str = f"{r['trades']}" if r['trades'] is not None else "N/A"
        print(f"{r['num']:<3} {r['name']:<25} {ret_str:<12} | {trades_str:<8}")

    # Find best performers
    valid_results = [r for r in results if r['return'] is not None]
    if valid_results:
        best_return = max(valid_results, key=lambda x: x['return'])
        worst_return = min(valid_results, key=lambda x: x['return'])

        print(f"\n{'-'*85}")
        print(f"🏆 Best Return:  Formula {best_return['num']} ({best_return['name']:<20}) {best_return['return']:+.2f}%")
        print(f"📉 Worst Return: Formula {worst_return['num']} ({worst_return['name']:<20}) {worst_return['return']:+.2f}%")

        avg_ret = sum([r['return'] for r in valid_results]) / len(valid_results)
        print(f"📊 Average:      {avg_ret:+.2f}%")

    print(f"\n{'='*90}\n")


if __name__ == "__main__":
    main()

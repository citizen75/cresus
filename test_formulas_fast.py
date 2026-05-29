#!/usr/bin/env python3
"""Test 10 Heikin Ashi entry formulas - extract from existing backtest results."""

import subprocess
import yaml
import json
import sys
from pathlib import Path
from datetime import datetime
import time

# 10 Heikin Ashi entry formulas for 10-day swing trading
FORMULAS = [
    {
        "name": "Strategy 1 (Très Agressif)",
        "formula": "sha_10_green[0]==1 && close[0] > open[0] && rsi_7[0] < 70"
    },
    {
        "name": "Strategy 2 (Agressif - Cassure)",
        "formula": "sha_10_green[0]==1 && sha_10_up[0]==1 && close[0] > sma_20[0]"
    },
    {
        "name": "Strategy 3 (Agressif - Momentum)",
        "formula": "sha_10_green[0]==1 && rsi_7[0] > 50 && rsi_7[0] < 70 && ema_10[0] > ema_20[0]"
    },
    {
        "name": "Strategy 4 (Modéré - Confirmation)",
        "formula": "sha_10_green[0]==1 && sha_10_green[-1]==1 && adx_14[0] > 20 && close[0] > ema_50[0]"
    },
    {
        "name": "Strategy 5 (Modéré - Alignement EMA)",
        "formula": "sha_10_green[0]==1 && ema_10[0] > ema_20[0] && ema_20[0] > ema_50[0] && rsi_7[0] < 70"
    },
    {
        "name": "Strategy 6 (Modéré - Rebond)",
        "formula": "sha_10_green[0]==1 && rsi_7[-1] < 40 && rsi_7[0] > 40 && close[0] > ema_50[0]"
    },
    {
        "name": "Strategy 7 (Conservateur - Double)",
        "formula": "sha_10_green[0]==1 && sha_10_green[-1]==1 && adx_14[0] > 25 && close[0] > sma_20[0]"
    },
    {
        "name": "Strategy 8 (Conservateur - Pull-back)",
        "formula": "sha_10_green[0]==1 && close[0] < sma_20[0] * 1.03 && close[0] > ema_50[0] && rsi_7[0] < 65"
    },
    {
        "name": "Strategy 9 (Conservateur - Trend)",
        "formula": "sha_10_green[0]==1 && ema_10[0] > ema_20[0] && ema_20[0] > ema_50[0] && adx_14[0] > 25 && rsi_7[0] < 70"
    },
    {
        "name": "Strategy 10 (Très Conservateur)",
        "formula": "sha_10_green[0]==1 && sha_10_green[-1]==1 && ema_10[0] > ema_20[0] && ema_20[0] > ema_50[0] && adx_14[0] > 25 && rsi_7[0] < 70"
    }
]

STRATEGY_PATH = Path.home() / ".cresus/db/strategies/cac_trend.yml"
BACKTEST_PATH = Path.home() / ".cresus/db/backtests/cac_trend"
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
    cmd = [
        "cresus", "backtest", "run", "cac_trend",
        START_DATE, END_DATE
    ]
    print(f"  Running: cresus backtest run cac_trend {START_DATE} {END_DATE}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return True
    except subprocess.TimeoutExpired:
        print("    ⚠️  Backtest timed out (180s)")
        return False
    except Exception as e:
        print(f"    ❌ Error running backtest: {e}")
        return False


def extract_metrics_from_json():
    """Extract metrics from the most recent backtest JSON."""
    # Find most recent backtest directory
    if not BACKTEST_PATH.exists():
        return None, None

    try:
        latest = max(BACKTEST_PATH.glob("*/metrics.json"), key=lambda p: p.parent.stat().st_mtime)
        with open(latest, 'r') as f:
            metrics = json.load(f)

        # Extract total return and win rate
        total_return = metrics.get("total_return_pct")
        win_rate = metrics.get("win_rate_pct")

        return total_return, win_rate
    except Exception as e:
        print(f"    ❌ Error extracting metrics: {e}")
        return None, None


def main():
    """Test all formulas."""
    print(f"\n{'='*80}")
    print(f"Testing 10 Heikin Ashi Entry Formulas for CAC40 (10-day swing trading)")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"{'='*80}\n")

    results = []

    for i, formula_config in enumerate(FORMULAS, 1):
        print(f"[{i}/10] {formula_config['name']}")
        print(f"  Formula: {formula_config['formula'][:60]}...")

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
                "win_rate": None,
                "status": "❌"
            })
            print("  Failed to run backtest\n")
            continue

        # Small delay to ensure file is written
        time.sleep(2)

        # Extract metrics
        return_pct, win_rate = extract_metrics_from_json()

        if return_pct is not None and win_rate is not None:
            status = "✅"
        elif return_pct is not None or win_rate is not None:
            status = "⚠️"
        else:
            status = "❌"

        result = {
            "num": i,
            "name": formula_config['name'],
            "formula": formula_config['formula'],
            "return": return_pct,
            "win_rate": win_rate,
            "status": status
        }
        results.append(result)

        ret_str = f"{return_pct:+.2f}%" if return_pct is not None else "N/A"
        wr_str = f"{win_rate:.1f}%" if win_rate is not None else "N/A"
        print(f"  {status} Return: {ret_str}, Win Rate: {wr_str}\n")

    # Print summary table
    print(f"{'='*80}")
    print("RESULTS SUMMARY")
    print(f"{'='*80}\n")

    print(f"{'#':<3} {'Strategy':<30} {'Return':<12} {'Win Rate':<12}")
    print(f"{'-'*57}")

    for r in results:
        ret_str = f"{r['return']:+.2f}%" if r['return'] is not None else "N/A"
        wr_str = f"{r['win_rate']:.1f}%" if r['win_rate'] is not None else "N/A"
        print(f"{r['num']:<3} {r['name']:<30} {ret_str:<12} {wr_str:<12}")

    # Find best performers
    valid_results = [r for r in results if r['return'] is not None]
    if valid_results:
        best_return = max(valid_results, key=lambda x: x['return'])
        valid_wr = [r for r in valid_results if r['win_rate'] is not None]
        best_winrate = max(valid_wr, key=lambda x: x['win_rate']) if valid_wr else None

        print(f"\n{'-'*57}")
        print(f"🏆 Best Return:  Strategy {best_return['num']} ({best_return['name']:<20}) {best_return['return']:+.2f}%")
        if best_winrate and best_winrate['win_rate']:
            print(f"🏆 Best Win Rate: Strategy {best_winrate['num']} ({best_winrate['name']:<20}) {best_winrate['win_rate']:.1f}%")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()

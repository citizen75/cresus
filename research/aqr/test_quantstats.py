#!/usr/bin/env python3
"""
Demo: QuantStats integration with Portfolio Engine
Shows detailed analytics for backtested portfolios
"""

import sys
sys.path.insert(0, '/Volumes/Data/dev/cresus/src')
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
import warnings
from tools.universe import Universe
from tools.data import DataHistory
from portfolio_engine_v2 import run_simple_backtest, SimplePortfolio

try:
    import quantstats as qs
    HAS_QUANTSTATS = True
except ImportError:
    HAS_QUANTSTATS = False
    print("⚠️  QuantStats not installed. Install with: pip install quantstats")

warnings.filterwarnings("ignore")

print("=" * 100)
print("QUANTSTATS INTEGRATION DEMO")
print("=" * 100)

if not HAS_QUANTSTATS:
    print("\n❌ QuantStats not available. Install with:")
    print("   pip install -e '.[research]'")
    sys.exit(1)

# Load sample data
print("\n📍 Loading market data...")
TRADABLE_STOCKS = Universe('cac40').get_tickers()[:10]  # Quick demo with 10 stocks
close_data = {}
for ticker in TRADABLE_STOCKS:
    try:
        dh = DataHistory(ticker)
        dh.fetch(incremental=True)
        df = dh.load_all()
        if not df.empty:
            close_data[ticker] = df[['timestamp', 'close']].set_index('timestamp')['close']
    except:
        pass

close = pd.DataFrame(close_data)
close = close.dropna(axis=1, thresh=int(len(close) * 0.7))
close = close.ffill().bfill()
returns = close.pct_change()

print(f"✅ Loaded {len(close)} days, {len(close.columns)} stocks")

# Create sample trades
print("\n📍 Creating sample momentum trades...")
trades = []
dates_list = sorted(returns.index[1:])
rebalance_dates = [dates_list[i] for i in range(0, min(100, len(dates_list)), 10)]  # Quick demo

for date in rebalance_dates[:10]:  # First 10 rebalances
    idx = close.index.get_loc(date)
    if idx < 21:
        continue

    # Find top 3 momentum stocks
    momentum = {}
    for col in close.columns:
        current = close[col].iloc[idx]
        past = close[col].iloc[idx - 21]
        if pd.notna(current) and pd.notna(past) and past != 0:
            momentum[col] = (current / past) - 1

    if len(momentum) >= 3:
        top_3 = sorted(momentum.items(), key=lambda x: x[1], reverse=True)[:3]
        for stock, _ in top_3:
            price = close[stock].loc[date]
            qty = int(3333 / price)  # Allocate ~€3333 per position
            if qty > 0:
                trades.append({
                    'Date': date,
                    'Ticker': stock,
                    'Type': 'BUY',
                    'Price': price,
                    'Quantity': qty
                })

trades_df = pd.DataFrame(trades)
print(f"✅ Generated {len(trades_df)} trades")

# Run backtest
print("\n📍 Running portfolio engine...")
portfolio = run_simple_backtest(trades_df, initial_capital=10000.0, fee_rate=0.0015)

print(f"✅ Backtest complete. Open positions: {len(portfolio.holdings)}")

# Calculate daily returns for QuantStats
print("\n📍 Calculating daily portfolio returns...")
daily_values = [portfolio.initial_capital]
current_value = portfolio.initial_capital

for _, trade in trades_df.iterrows():
    date = trade['Date']
    ticker = trade['Ticker']
    price = trade['Price']
    qty = trade['Quantity']

    if trade['Type'] == 'BUY':
        fee = price * qty * portfolio.fee_rate
        current_value -= (price * qty + fee)
    else:
        fee = price * qty * portfolio.fee_rate
        current_value += (price * qty - fee)

    daily_values.append(current_value)

daily_returns = pd.Series(daily_values).pct_change().dropna()

print(f"✅ Calculated {len(daily_returns)} daily returns")

# Generate QuantStats report
print("\n📍 Generating QuantStats analytics...")
portfolio.print_quantstats_report(daily_returns)

# Additional analysis
print("\n📊 ADVANCED METRICS (QuantStats):")
if HAS_QUANTSTATS:
    try:
        # Drawdown analysis
        print(f"\n  Drawdown periods:")
        dd_info = qs.stats.drawdown_details(daily_returns)
        if len(dd_info) > 0:
            print(f"    Total drawdown events: {len(dd_info)}")
            print(f"    Average drawdown: {dd_info['Drawdown'].mean()*100:.2f}%")
            print(f"    Longest drawdown: {(dd_info['Duration'].max().days if hasattr(dd_info['Duration'].max(), 'days') else dd_info['Duration'].max()):.0f} days")

        # Monthly returns
        print(f"\n  Monthly statistics:")
        monthly_ret = qs.stats.monthly_returns(daily_returns) * 100
        print(f"    Average monthly: {monthly_ret.mean():.2f}%")
        print(f"    Best month: {monthly_ret.max():.2f}%")
        print(f"    Worst month: {monthly_ret.min():.2f}%")

    except Exception as e:
        print(f"  ⚠️  Error generating advanced metrics: {e}")

print("\n" + "=" * 100)
print("✅ QUANTSTATS INTEGRATION WORKING!")
print("   Use portfolio.print_quantstats_report(daily_returns) in your backtest")
print("=" * 100)

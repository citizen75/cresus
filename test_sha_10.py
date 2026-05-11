#!/usr/bin/env python3
"""Test script to analyze sha_10_green indicator"""
import sys
from pathlib import Path

src_path = Path(".").resolve() / "src"
sys.path.insert(0, str(src_path))

from agents.data import DataAgent
from core.context import AgentContext

# Step 1: Load data via DataAgent
print("Loading data via DataAgent...")
context = AgentContext()
data_agent = DataAgent("test_agent", context)
result = data_agent.process({"tickers": ["FR0007052782"]})

# Get data_history from context
data_history = context.get("data_history")

ticker = "FR0007052782"
df = data_history[ticker].copy()

print(f"✓ Loaded {len(df)} rows for {ticker}")
print(f"  Date range: {df['timestamp'].iloc[-1]} to {df['timestamp'].iloc[0]}")
print()

# Step 2: Indicators already calculated by DataAgent
print("✓ Indicators already calculated by DataAgent")

print(f"  Columns: {df.columns.tolist()}")
print()

# Step 3: Check sha_10_green values
print("Analyzing sha_10_green indicator...")
print(f"  Data type: {df['sha_10_green'].dtype}")
print(f"  Unique values: {df['sha_10_green'].unique()}")
print()

# Step 4: Count occurrences
count_green = (df['sha_10_green'] == 1).sum()
count_red = (df['sha_10_red'] == 1).sum()
total = len(df)

print(f"Results:")
print(f"  Total rows: {total}")
print(f"  sha_10_green == 1 (candle is green): {count_green} ({100*count_green/total:.1f}%)")
print(f"  sha_10_red == 1 (candle is red):     {count_red} ({100*count_red/total:.1f}%)")
print()

# Step 5: Verify they're mutually exclusive
print(f"Mutual exclusivity check:")
both_true = ((df['sha_10_green'] == 1) & (df['sha_10_red'] == 1)).sum()
both_false = ((df['sha_10_green'] == 0) & (df['sha_10_red'] == 0)).sum()
print(f"  Both green and red == 1: {both_true} (should be 0)")
print(f"  Both green and red == 0: {both_false} (should be 0)")
if both_true == 0 and both_false == 0:
    print(f"  ✓ Perfect mutual exclusivity")
print()

# Step 6: Show some samples
print("Sample of latest 5 rows:")
print(df[['timestamp', 'open', 'close', 'sha_10', 'sha_10_green', 'sha_10_red']].head().to_string())

#!/usr/bin/env python3
"""Display data_history rows where sha_10_green == 1 since 2026-01-01"""
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

src_path = Path(".").resolve() / "src"
sys.path.insert(0, str(src_path))

from agents.data import DataAgent
from core.context import AgentContext

# Load data via DataAgent
print("Loading data via DataAgent...")
context = AgentContext()
data_agent = DataAgent("test_agent", context)
result = data_agent.process({"tickers": ["FR0007052782"]})

# Get data_history from context
data_history = context.get("data_history")
ticker = "FR0007052782"
df = data_history[ticker].copy()

# Convert timestamp to datetime if needed
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filter to since 2026-01-01
target_date = pd.to_datetime("2026-01-01")
df_filtered = df[df['timestamp'] >= target_date].copy()

print(f"✓ Loaded {len(df)} total rows, {len(df_filtered)} rows since 2026-01-01")
print()

# Filter where sha_10_green == 1
green_candles = df_filtered[df_filtered['sha_10_green'] == 1].copy()

print(f"Rows where sha_10_green == 1 (since 2026-01-01): {len(green_candles)}")
print("=" * 140)
print(green_candles[['timestamp', 'open', 'close', 'sha_10', 'sha_10_green', 'sha_10_red', 'rsi_14', 'ema_20', 'adx_20']].to_string(index=False))

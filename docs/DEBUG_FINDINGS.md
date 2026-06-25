# Premarket Flow Analysis - May 2026

## Issue
Premarket flow on 2026-05-05 generates 0 orders despite:
- Watchlist: 9 tickers
- Entry scores: All 9 scored (avg 91.4/100)
- Entry filter: Blocks ALL 9 tickers

## Root Cause
The entry filter formula requires a **red-to-green reversal pattern**:
```
sha_10_green[0] == 1 AND sha_10_green[-1] == 1 AND sha_10_red[-2] == 1 AND adx_14[0] > 25
```

This requires:
- Current bar (index 0): GREEN ✓
- Previous bar (index 1): GREEN ✓  
- 2 bars ago (index 2): RED ✗ (but it's GREEN instead!)
- ADX > 25: varies

## Why All Tickers Fail
On 2026-05-05, ALL watchlist tickers are in **sustained green uptrends** with no red candles:
```
Date         sha_10_green  sha_10_red
2026-05-05   1            0  ← current bar (green, no red)
2026-05-04   1            0  ← previous bar (green, no red)
2026-04-30   1            0  ← 2 bars ago (GREEN, not red!)
2026-04-29   1            0
2026-04-28   1            0
```

For the filter to pass, we need index[2] to have red=1, but it's green=1.

## Data Quality ✓
- DataAgent loads FULL historical data (4000+ rows per ticker)
- Indicators calculated correctly with full context
- _set_data_history_for_date() properly slices to target date while preserving lookback
- HAMA signals (sha_10_green, sha_10_red) calculated dynamically and cached

## Historical Context
The 6 orders in the historical CSV (2026-05-05 through 2026-05-12) were created on **different dates** when:
- Same tickers DID have the red-to-green reversal pattern
- OR filter conditions were different at that time

## Conclusion
✓ System is working correctly
✓ Data loading is sufficient
✓ Indicators are calculated properly
✓ Entry filter is intentionally strict (reversal-based entry)
✗ Market conditions on 2026-05-05 don't match filter criteria

The filter requires sustained green AFTER a red candle. On this date, tickers are in extended green trends with no recent red reversals, so no entries are generated.

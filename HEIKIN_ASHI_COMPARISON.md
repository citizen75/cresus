# Heikin Ashi Algorithm Comparison: Cresus vs TradingView

## Standard Heikin Ashi Formula (Industry Standard)

### HA_Close
```
HA_Close = (Open + High + Low + Close) / 4
```

### HA_Open
```
HA_Open[0] = (Open + Close) / 2  [First bar: midpoint of open-close]
HA_Open[n] = (HA_Open[n-1] + HA_Close[n-1]) / 2  [Subsequent bars]
```

### HA_High
```
HA_High = MAX(High, HA_Open, HA_Close)
```

### HA_Low
```
HA_Low = MIN(Low, HA_Open, HA_Close)
```

---

## Cresus Implementation

### Source
- **File**: `src/tools/indicators/core/heikin_ashi.py`
- **Library**: pandas-ta (pandas_ta_classic)
- **Method**: Uses `pandas_ta.ha()` function

### Formulas in Codebase
```python
# Lines 19-22: Documented formulas
HA Close = (Open + High + Low + Close) / 4
HA Open = (previous HA Open + previous HA Close) / 2
HA High = max(High, HA Open, HA Close)
HA Low = min(Low, HA Open, HA Close)
```

### Implementation Details
```python
# Line 87: Delegates to pandas-ta
ha = pandas_ta.ha(df["Open"], df["High"], df["Low"], df["Close"])

# Lines 91-94: Extracts components
ha_open_series = pd.Series(ha["HA_open"].values[-result_len:])
ha_high_series = pd.Series(ha["HA_high"].values[-result_len:])
ha_low_series = pd.Series(ha["HA_low"].values[-result_len:])
ha_close_series = pd.Series(ha["HA_close"].values[-result_len:])
```

### Color Signals (Regular HA)
```python
# Lines 97-98
ha_green = (ha_close_series > ha_open_series).astype(int)  # Bullish
ha_red = (ha_close_series < ha_open_series).astype(int)    # Bearish
```

---

## Smooth Heikin Ashi (SHA) - Standard Implementation

### TradingView Approach (Community Standard)

**Three-Step Process:**

1. **Pre-HA Smoothing**: Smooth raw OHLC prices with MA
   ```
   Smoothed_Open = MA(Open, period_1)
   Smoothed_High = MA(High, period_1)
   Smoothed_Low = MA(Low, period_1)
   Smoothed_Close = MA(Close, period_1)
   ```

2. **Apply Standard HA Formula**: Use smoothed prices
   ```
   HA_Close = (Smoothed_O + Smoothed_H + Smoothed_L + Smoothed_C) / 4
   HA_Open = (prev_HA_Open + prev_HA_Close) / 2
   HA_High = MAX(Smoothed_H, HA_Open, HA_Close)
   HA_Low = MIN(Smoothed_L, HA_Open, HA_Close)
   ```

3. **Post-HA Smoothing**: Smooth HA components with MA (optional)
   ```
   SHA_Open = MA(HA_Open, period_2)
   SHA_Close = MA(HA_Close, period_2)
   SHA_High = MA(HA_High, period_2)
   SHA_Low = MA(HA_Low, period_2)
   ```

### Cresus Implementation

**Two-Step Process:**

1. **Calculate Standard HA**: No pre-smoothing of prices
   ```python
   ha = pandas_ta.ha(df["Open"], df["High"], df["Low"], df["Close"])
   ```

2. **Post-HA Smoothing Only**: Apply EMA to HA components
   ```python
   sha_open = pandas_ta.ema(ha["HA_open"], length=period)
   sha_high = pandas_ta.ema(ha["HA_high"], length=period)
   sha_low = pandas_ta.ema(ha["HA_low"], length=period)
   sha_close = pandas_ta.ema(ha["HA_close"], length=period)
   ```

### Wick-Based Indicators (Custom Enhancement)
```python
# Lines 203-204: Distinguishes candle quality by wick presence
sha_up = (sha_close > sha_open) & (bottom_wick_ratio < 0.20)
sha_down = (sha_close < sha_open) & (top_wick_ratio < 0.20)
```

- **sha_up**: Bullish candles with bottom wick < 20% of body
- **sha_down**: Bearish candles with top wick < 20% of body

---

## Comparison Summary

| Feature | Cresus | TradingView | Status |
|---------|--------|------------|--------|
| **Standard HA Formula** | (O+H+L+C)/4 | (O+H+L+C)/4 | ✓ Identical |
| **HA_Open calculation** | (prev_open + prev_close)/2 | (prev_open + prev_close)/2 | ✓ Identical |
| **HA_High formula** | MAX(H, HA_O, HA_C) | MAX(H, HA_O, HA_C) | ✓ Identical |
| **HA_Low formula** | MIN(L, HA_O, HA_C) | MIN(L, HA_O, HA_C) | ✓ Identical |
| **Color signals** | Green (C>O), Red (C<O) | Green (C>O), Red (C<O) | ✓ Identical |
| **SHA Pre-smoothing** | ❌ None (direct HA calc) | ✓ Optional MA on OHLC | ⚠️ Difference |
| **SHA Post-smoothing** | ✓ EMA on HA components | ✓ Optional MA on HA | ✓ Similar |
| **Smoothing type** | EMA only (fixed) | Configurable MA types | ⚠️ Less flexible |
| **Wick detection** | ✓ 20% body ratio threshold | ❌ Not in standard | ✓ Cresus unique |

---

## Key Findings

### ✓ Correct Implementation
The Cresus implementation of **standard Heikin Ashi** is **100% correct** and matches the industry-standard formula and TradingView's approach. The pandas-ta library implements the canonical algorithm properly.

### ✓ Data Consistency
- Both implementations require historical bar data (current bar depends on previous bar's HA_Open and HA_Close)
- Cresus correctly handles this by allowing `history_df` parameter for extended lookback
- Both sort data ascending (oldest first) for proper sequential calculation

### ⚠️ Key Differences: Cresus vs TradingView SHA

**TradingView Approach (More Flexible):**
- Pre-smooths raw OHLC prices before HA calculation
- Then applies optional post-smoothing to HA components
- Allows configurable MA types (SMA, EMA, WMA, etc.)
- Single or dual smoothing option

**Cresus Approach (Simpler, Focused):**
- Skips pre-smoothing of prices
- Applies EMA smoothing only to final HA components
- Fixed to EMA (no MA type selection)
- Single-stage post-smoothing

**Impact**: TradingView's pre-smoothing approach may reduce more noise at the cost of additional lag, while Cresus's approach is more direct but less configurable.

### ✓ Unique Features in Cresus
1. **Wick Detection Algorithm**: Not available in standard TradingView
   - `sha_up`: Bullish candles with bottom wick < 20% of body
   - `sha_down`: Bearish candles with top wick < 20% of body
   - Useful for identifying clean trend candles vs. indecisive ones
   
2. **Automatic Multi-Component Output**: All SHA variants generated automatically
   - `sha_open`, `sha_high`, `sha_low`, `sha_close`
   - `sha_green`, `sha_red`, `sha_bullish`
   - `sha_up`, `sha_down`

### ✓ Standard HA Formula Correctness
- No discrepancies for standard Heikin Ashi
- pandas-ta's `ha()` function correctly implements canonical formula
- Sorting and sequential dependencies properly handled

---

## Sources

### Standard Heikin Ashi
- [LiteFinance - Heikin-Ashi Formula Calculation](https://www.litefinance.org/blog/for-beginners/types-of-forex-charts/heikin-ashi-candles/)
- [TradingView Support - Understanding Heikin Ashi Charts](https://www.tradingview.com/support/solutions/43000619436-understanding-heikin-ashi-charts/)
- [TradingView Pine Script - Non-standard Charts Data](https://www.tradingview.com/pine-script-docs/concepts/non-standard-charts-data/)
- [NinjaTrader - Heikin Ashi Candlestick Charts Explained](https://ninjatrader.com/futures/blogs/heikin-ashi-candlestick-charts-explained/)
- [CFI - Heikin-Ashi Technique Overview](https://corporatefinanceinstitute.com/resources/career-map/sell-side/capital-markets/heikin-ashi-technique/)

### Smooth/Smoothed Heikin Ashi
- [TradingView - Smoothed Heiken Ashi by TheBacktestGuy](https://www.tradingview.com/script/pjl3mIvc-Smoothed-Heiken-Ashi/)
- [TradingView - Heikin-Ashi Smoothed with MA Types by CryptoJoncis](https://www.tradingview.com/script/Oiq9yfPg-Heikin-Ashi-Smoothed-with-option-to-change-MA-types-CryptoJoncis/)
- [BarChart - Heikin-Ashi Smoothed Indicator](https://www.barchart.com/education/technical-indicators/heikin-ashi-smoothed)

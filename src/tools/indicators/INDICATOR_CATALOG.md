# Technical Indicators Catalog

Complete reference documentation for all 48 technical indicators in the module.

---

## MOMENTUM INDICATORS

### RSI (Relative Strength Index)
**Syntax:** `rsi_<period>`  
**Parameters:**
- `period` (int, default=14): Lookback period in days

**Description:**
Oscillator measuring the magnitude of recent price changes to evaluate overbought/oversold conditions. Ranges from 0 to 100.

**Formula:**
```
RS = Average Gain / Average Loss (over period)
RSI = 100 - (100 / (1 + RS))
```

**Output:** Series (0-100)

**Interpretation:**
- RSI > 70: Overbought (potential sell signal)
- RSI < 30: Oversold (potential buy signal)
- RSI = 50: Neutral
- Divergences (price makes new high but RSI doesn't): Reversal signal

**Edge Cases:**
- Returns 50 for initial NaN values (neutral default)
- Validates output to ensure 0-100 range

**Status:** ✅ Complete, well-tested with pandas-ta

---

### MACD (Moving Average Convergence Divergence)
**Syntax:** `macd_<fast>_<slow>_<signal>`  
**Parameters:**
- `fast` (int, default=12): Fast EMA period
- `slow` (int, default=26): Slow EMA period
- `signal` (int, default=9): Signal line EMA period

**Description:**
Trend-following momentum indicator showing relationship between two moving averages. Returns histogram showing MACD minus signal line.

**Formula:**
```
MACD = EMA(12) - EMA(26)
Signal = EMA(MACD, 9)
Histogram = MACD - Signal
```

**Output:** Dict with keys:
- `macd` / `macd_line`: Main MACD line
- `macd_signal`: Signal line (EMA of MACD)
- `macd_histogram`: Difference (often used for signals)

**Interpretation:**
- MACD > Signal: Bullish (MACD crossing above signal = buy)
- MACD < Signal: Bearish (crossing below = sell)
- Histogram zero-crossings: Momentum changes

**Issues:**
- ⚠️ Returns duplicate keys: `macd` and `macd_line` are identical
- Histogram not automatically returned in some contexts

**Status:** ✅ Works, pandas-ta, but needs cleanup

---

### ROC (Rate of Change)
**Syntax:** `roc_<period>`  
**Parameters:**
- `period` (int, default=12): Lookback period in days

**Description:**
Momentum oscillator measuring rate at which price is changing. Positive = price rising faster, negative = falling.

**Formula:**
```
ROC = ((Close - Close[period]) / Close[period]) * 100
```

**Output:** Series (percentage, can be negative)

**Interpretation:**
- ROC > 0: Bullish momentum
- ROC < 0: Bearish momentum
- Extreme values: Potential reversal (too extended)
- Zero-crossings: Momentum changes

**Similarities:**
- Very similar to `chgpct_<period>` (percentage change)
- Difference: ROC includes smoothing in some implementations

**Status:** ✅ Complete

---

## TREND INDICATORS

### EMA (Exponential Moving Average)
**Syntax:** `ema_<period>`  
**Parameters:**
- `period` (int, default=20): EMA period in days

**Description:**
Weighted moving average giving more importance to recent prices. Smoother than SMA and responds faster to price changes.

**Formula:**
```
Multiplier = 2 / (period + 1)
EMA = (Close - EMA[previous]) × Multiplier + EMA[previous]
```

**Output:** Series

**Interpretation:**
- Price > EMA: Uptrend
- Price < EMA: Downtrend
- EMA slope: Trend strength
- Multiple EMAs: Fast vs slow (EMA(5) above EMA(20) = bullish cross)

**Uses:**
- Trend identification
- Support/resistance levels
- Moving average crosses

**Implementation:** Uses pandas-ta canonical library

**Status:** ✅ Complete, well-tested

---

### SMA (Simple Moving Average)
**Syntax:** `sma_<period>`  
**Parameters:**
- `period` (int, default=50): SMA period in days

**Description:**
Simple average of closing prices over a period. Less responsive than EMA but cleaner for support/resistance.

**Formula:**
```
SMA = Sum(Close[period]) / period
```

**Output:** Series

**Common Periods:**
- SMA(20): Short-term trend
- SMA(50): Medium-term trend
- SMA(200): Long-term trend (yearly average)

**Interpretation:**
- Price > SMA(200): Long-term uptrend
- SMA(20) > SMA(50): Short-term stronger than medium
- Golden Cross: SMA(50) > SMA(200) = strong buy
- Death Cross: SMA(50) < SMA(200) = strong sell

**Implementation:** Uses pandas-ta

**Status:** ✅ Complete

---

### ADX (Average Directional Index)
**Syntax:** `adx_<period>`  
**Parameters:**
- `period` (int, default=14): Smoothing period

**Description:**
Measures trend strength (not direction) ranging 0-100. High ADX = strong trend, low ADX = weak/ranging market.

**Formula:**
```
+DI = (UpMove - DownMove) smoothed over period
ADX = SMA(|+DI - -DI| / (+DI + -DI) * 100)
Force = -1 (strong down) | 0 (ranging) | 1 (strong up)
```

**Output:** Dict with:
- `adx`: Trend strength (0-100)
- `force`: Trend direction (-1/0/1)

**Interpretation:**
- ADX > 25: Strong trend (good for trending strategies)
- ADX 20-25: Moderate trend
- ADX < 20: Weak trend / ranging market
- ADX rising: Trend strengthening
- ADX falling: Trend weakening

**⚠️ Issues:**
- Magic thresholds (20, 25) undocumented
- Uses proprietary `force` component

**Status:** ✅ Works, but needs documentation

---

### EMA % Change
**Syntax:** `ema_<ema_period>_chgpct_<change_period>`  
**Parameters:**
- `ema_period` (int, default=20): EMA calculation period
- `change_period` (int, default=5): Lookback for % change

**Description:**
Percentage change of EMA over N days. Combines EMA smoothing with momentum calculation.

**Formula:**
```
EMA = EMA(close, ema_period)
Change% = ((EMA - EMA[change_period]) / EMA[change_period]) * 100
```

**Output:** Series (percentage, can be negative)

**Use Cases:**
- EMA momentum tracking
- Trend acceleration measurement
- Cross-checks with price momentum

**⚠️ Issues:**
- Not properly registered in parser
- Non-standard double-underscore syntax

**Status:** ⚠️ Implemented but broken registration

---

### HAMA (Hull Average / NST Version)
**Syntax:** `hama_<len_open>_<len_close>_<ema_line>`  
**Parameters:**
- `len_open` (int, default=25): Open calculation length
- `len_close` (int, default=20): Close calculation length
- `ema_line` (int, default=55): EMA smoothing length

**Description:**
Custom moving average combining Hull moving average concepts with Heiken Ashi smoothing. Different from standard Hull MA.

**⚠️ Important:** This is NOT the standard "Hull MA" from technical analysis - it's a proprietary NST version.

**Formula:**
Combines open/close weighting with exponential smoothing (custom).

**Output:** Series

**⚠️ Issues:**
- Documentation doesn't match actual parameters
- Non-standard implementation
- Confusing naming (sounds like Heikin Ashi)

**Status:** ⚠️ Complete but poorly documented

---

## VOLATILITY INDICATORS

### ATR (Average True Range)
**Syntax:** `atr_<period>`  
**Parameters:**
- `period` (int, default=14): Smoothing period

**Description:**
Measures market volatility by calculating average of true ranges. Higher ATR = greater volatility, lower = consolidation.

**Formula:**
```
TR = max(High - Low, |High - Close[prev]|, |Low - Close[prev]|)
ATR = SMA(TR, period)
```

**Output:** Series (positive, never negative)

**Interpretation:**
- High ATR: Market very volatile, larger price swings
- Low ATR: Market consolidating, tight ranges
- ATR rising: Volatility increasing
- Used for: Position sizing, stop-loss levels, breakout detection

**Implementation:** pandas-ta canonical

**Status:** ✅ Complete, well-tested

---

### Bollinger Bands (BB)
**Syntax:** `bb_<period>_<std_dev>`  
**Parameters:**
- `period` (int, default=20): SMA calculation period
- `std_dev` (float, default=2.0): Standard deviation multiplier

**Description:**
Volatility bands plotted above/below middle SMA. Price touches bands = potential reversal signal.

**Formula:**
```
Middle = SMA(close, period)
StdDev = Standard Deviation of close over period
Upper = Middle + (std_dev × StdDev)
Lower = Middle - (std_dev × StdDev)
```

**Output:** Dict with:
- `bb`: Bollinger Bands (main output)
- `bb_upper`: Upper band
- `bb_middle`: Middle band (SMA)
- `bb_lower`: Lower band

**Interpretation:**
- Price > upper band: Overbought
- Price < lower band: Oversold
- Bands touching: Volatility squeeze (breakout coming)
- Bands expanding: Volatility increasing
- Bands contracting: Consolidation phase

**Status:** ✅ Complete, well-tested

---

### ATR Variants: Parkinson & Rogers-Satchell

**Parkinson Volatility**
**Syntax:** `parkinson_<period>`  
**Description:** Alternative volatility measure using high-low range only (ignores closes). Often more efficient than ATR.

**⚠️ Custom formula** - Not using pandas-ta, untested

**Rogers-Satchell Volatility**
**Syntax:** `rs_<period>`  
**Description:** Volatility measure for gapped markets using high-close and close-low. Good for markets with significant gaps.

**⚠️ Custom formula with lambda** - Complex, untested, potential performance issues

**Status:** ⚠️ Both custom implementations, need validation

---

## VOLUME INDICATORS

### A/D (Accumulation/Distribution)
**Syntax:** `ad`  
**Description:**
Cumulative line using volume and price movement. Positive = accumulation, negative = distribution.

**Formula:**
```
MFM = ((Close - Low) - (High - Close)) / (High - Low)
A/D = Previous A/D + (MFM × Volume)
```

**Output:** Series (cumulative, ever-increasing or decreasing)

**⚠️ Issues:**
- Poor error handling for missing columns
- Can return garbage with wrong column names

**Status:** ⚠️ Works but fragile

---

### OBV (On-Balance Volume)
**Syntax:** `obv`  
**Description:**
Cumulative volume indicator: adds volume on up days, subtracts on down days. Shows if volume supports price move.

**Formula:**
```
If Close > Close[prev]: OBV = Previous OBV + Volume
If Close < Close[prev]: OBV = Previous OBV - Volume
If Close = Close[prev]: OBV = Previous OBV
```

**Output:** Series (cumulative)

**Interpretation:**
- OBV rising with price: Strong uptrend (volume confirms)
- OBV falling while price rises: Weakness (volume doesn't confirm)
- OBV divergence: Precursor to reversal

**Status:** ✅ Complete

---

### MFI (Money Flow Index)
**Syntax:** `mfi_<period>`  
**Parameters:**
- `period` (int, default=14): Calculation period

**Description:**
Volume-weighted RSI. Ranges 0-100. Combines price and volume to show money flow direction.

**Formula:**
```
Typical Price = (High + Low + Close) / 3
Money Flow = Typical Price × Volume
Positive MF: If Close > Close[prev]
Negative MF: If Close < Close[prev]
MFI = 100 - (100 / (1 + (PMF Sum / NMF Sum)))
```

**Output:** Series (0-100)

**Interpretation:**
- MFI > 80: Overbought (potential sell)
- MFI < 20: Oversold (potential buy)
- Divergences: Price makes new high but MFI doesn't = reversal signal

**Implementation:** pandas-ta

**Status:** ✅ Complete

---

### CMF (Chaikin Money Flow)
**Syntax:** `cmf_<period>`  
**Parameters:**
- `period` (int, default=20): Calculation period

**Description:**
Money flow indicator ranging -1 to 1. Positive = accumulation (buyers in control), negative = distribution.

**Formula:**
```
MFM = ((Close - Low) - (High - Close)) / (High - Low)
CMF = Sum(MFM × Volume) / Sum(Volume) over period
```

**Output:** Series (-1 to 1)

**Interpretation:**
- CMF > 0: Accumulation phase
- CMF < 0: Distribution phase
- Strong CMF (>0.3/-0.3): Conviction in direction
- Weak CMF: Indecision

**Status:** ✅ Complete

---

### VWAP (Volume Weighted Average Price)
**Syntax:** `vwap[_<anchor>]`  
**Parameters:**
- `anchor` (optional): None (session), int (bar number), or str (date)

**Description:**
Cumulative volume-weighted price. Traders use it as dynamic support/resistance.

**Formula:**
```
VWAP = Σ(Typical Price × Volume) / Σ(Volume)
Typical Price = (High + Low + Close) / 3
```

**Output:** Series

**Use Cases:**
- Trading signal: Price > VWAP (bullish), Price < VWAP (bearish)
- Support/resistance: Dynamic levels that respect volume
- Institutional traders reference: Anchor at session open

**⚠️ Issues:**
- Anchor parsing complex; requires careful date handling
- Error messages unclear

**Status:** ⚠️ Works but confusing API

---

### Volume MA
**Syntax:** `volume_sma_<period>`  
**Parameters:**
- `period` (int, default=20): SMA period

**Description:**
Simple moving average of trading volume. Shows if current volume is above/below average.

**Formula:**
```
Volume MA = SMA(Volume, period)
```

**Output:** Series

**Use Cases:**
- Volume breakout: Volume > Volume MA × 1.5 = potential move
- Volume divergence: Price ATH but volume MA declining
- Market participation tracking

**Status:** ✅ Complete

---

## SUPPORT & RESISTANCE INDICATORS

### Pivot Points
**Syntax:** `pivot_<method>`  
**Methods:**
- `pivot_classic`: Standard pivot point
- `pivot_camarilla`: Tighter bands
- `pivot_woodie`: Weighted average
- `pivot_demark`: Alternative formula

**Description:**
Support/resistance levels calculated from previous session OHLC. Used by floor traders, algorithms, and institutions.

**Formula (Classic):**
```
Pivot = (High + Low + Close) / 3
Resistance = (2 × Pivot) - Low
Support = (2 × Pivot) - High
```

**⚠️ CRITICAL Issue:**
Only uses latest OHLC value - returns constant series across all bars.
Only practical for daily timeframe analysis.

**Status:** ⚠️ Works for daily only; needs clarification

---

### Support & Resistance Levels
**Syntax:** `support_<period>`, `resistance_<period>`  
**Parameters:**
- `period` (int): Lookback period

**Description:**
Horizontal support (swings lows) and resistance (swing highs) over N periods.

**Output:** Series

**Status:** ✅ Complete

---

### Lowest / Highest
**Syntax:** `lowest_<period>`, `highest_<period>`  
**Parameters:**
- `period` (int): Lookback period

**Description:**
Lowest low and highest high over N periods. Used for breakout detection.

**Output:** Series

**Uses:**
- Donchian Channel bottom (20-period lowest)
- Breakout triggers (price breaks above 52-week high)
- Stop-loss placement

**Status:** ✅ Complete

---

## CHANGE INDICATORS

### Chgpct (Percentage Change)
**Syntax:** `chgpct_<period>`  
**Parameters:**
- `period` (int, default=1): Lookback days

**Description:**
Percentage change of closing price over N days.

**Formula:**
```
Chgpct% = ((Close - Close[period]) / Close[period]) * 100
```

**Output:** Series (percentage, can be negative)

**Interpretation:**
- Positive: Price risen over period
- Negative: Price fallen over period
- Magnitude: Speed of change

**⚠️ Issues:**
- Duplicate of `change_pct` (100% identical code)
- Both registered; confusing which to use

**Status:** 🔴 Duplicate, needs cleanup

---

### Change Log
**Syntax:** `chglog_<period>`  
**Parameters:**
- `period` (int, default=1): Lookback days

**Description:**
Natural logarithm of price ratio. Used in some advanced analysis for better distribution properties.

**Formula:**
```
Chglog = ln(Close / Close[period])
```

**Output:** Series

**Why Log Returns?**
- Better statistical properties for modeling
- Assumes percentage returns rather than absolute
- More stable for long time series

**Status:** ✅ Complete

---

## CANDLESTICK INDICATORS

### Heikin Ashi (HA)
**Syntax:** `ha[_<component>]`  
**Components:**
- `ha`: Main candles
- `ha_open`, `ha_close`, `ha_high`, `ha_low`: Components
- `ha_green`: Bullish candles (1 = green, 0 = red)
- `ha_red`: Bearish candles

**Description:**
Alternative candlestick format smoothing price action. Uses average of current + previous bars.

**Formula:**
```
HA_Close = (Open + High + Low + Close) / 4
HA_Open = (HA_Open[prev] + HA_Close[prev]) / 2
HA_High = max(High, HA_Open, HA_Close)
HA_Low = min(Low, HA_Open, HA_Close)
```

**Output:** Series or Dict with components

**Interpretation:**
- HA trend more apparent than regular candles
- Wicks indicate price rejection
- Series of same-colored candles: strong trend

**Status:** ✅ Complete

---

### SHA (Smooth Heikin Ashi)
**Syntax:** `sha_<period>[_<component>]`  
**Components:**
- `sha_<period>`: Main smoothed HA
- `sha_<period>_close`: Close price
- `sha_<period>_green`: Bullish (binary)
- `sha_<period>_red`: Bearish (binary)
- `sha_<period>_up`: ⚠️ Bullish without bottom wick (BROKEN)
- `sha_<period>_down`: ⚠️ Bearish without top wick (BROKEN)

**Description:**
Heikin Ashi with additional EMA smoothing over N periods.

**🔴 CRITICAL Issues:**
- `sha_up` and `sha_down` logic is incomplete/disabled
- Returns standard green/red instead of wick detection

**Status:** 🔴 sha_up/sha_down broken, others work

---

## INDICATOR SELECTION GUIDE

### For Trend Identification
- **Primary:** EMA (fast) or SMA (traditional)
- **Confirmation:** ADX (shows strength)
- **Candlestick:** SHA or HA (visual confirmation)

### For Reversal Detection
- **Momentum:** RSI (overbought/oversold)
- **Volume:** MFI (money flow divergence)
- **Levels:** Pivot Points, Bollinger Bands (extremes)

### For Volatility Assessment
- **Direct:** ATR, Bollinger Bands width
- **Alternative:** Parkinson or Rogers-Satchell
- **Volume-based:** CMF (divergence)

### For Volume Analysis
- **Directional:** A/D, OBV (accumulation/distribution)
- **Ratio:** CMF (money flow), MFI (flow index)
- **Weighted:** VWAP (trader reference level)

### For Breakout Detection
- **Price Range:** Highest/Lowest (Donchian breakout)
- **Volume:** Volume MA ratio
- **Support/Resistance:** Pivot Points, SA levels

---

## TECHNICAL NOTES

### Parameters & Periods
- **Standard Periods:** RSI(14), EMA(12), SMA(50), ATR(14), MACD(12,26,9)
- **Day Trading:** Shorter periods (5, 7, 10)
- **Swing Trading:** Medium periods (14, 20, 21)
- **Position Trading:** Longer periods (50, 100, 200)

### Multiple Timeframes
Most indicators work on any timeframe. Common approach:
- Hourly: EMA(5), RSI(7) for quick signals
- Daily: EMA(20), RSI(14), Volume MA(20) for trends
- Weekly: SMA(50), ADX(14) for major trends

### Indicator Combinations
Common setups:
1. **Trend + Momentum:** EMA cross + RSI overbought
2. **Trend + Volume:** ADX rising + Volume MA spike
3. **Reversal + Confirmation:** RSI extreme + MACD divergence
4. **Support/Resistance:** Pivot Points + Bollinger Band extremes

---

**Total Indicators:** 48  
**Categories:** 7  
**Fully Tested:** ~30  
**Needs Verification:** ~10  
**Critical Issues:** 2 (SHA_UP/DOWN, chgpct duplicate)

Last updated: 2026-06-18

# Orders Analytics - Complete Master Guide

## Quick Start

Run orders analytics for your strategy:
```bash
cresus flow run portfolio_analysis momentum_cac --backtest
```

Output includes comprehensive order execution analysis with metrics and recommendations.

---

## What Orders Analytics Analyzes

The OrdersAnalysisAgent examines 6 key dimensions of order execution:

### 1. Position Sizing Consistency
- How similar are order sizes?
- Are they following the position_size formula?
- Any zero-quantity orders?

**Example:**
```
Average Buy Size: 36.58 shares
Size Consistency: 0.0% ← Problem: No consistency!
```

### 2. Order Timing Patterns
- How many orders per day?
- Is there a peak hour?
- Is order generation steady or bursty?

**Example:**
```
Avg Orders/Day: 3.6
Max Orders/Day: 23 ← Problem: Very bursty!
Peak Hour: 14 (2 PM)
```

### 3. Buy/Sell Order Balance
- Are exits strong as entries?
- What's the buy/sell ratio?
- Total quantity and value balanced?

**Example:**
```
Buy/Sell Ratio: 1.57x ✓ Good (balanced)
Total Buy Qty: 5,121 shares
Total Sell Qty: 5,030 shares ✓ Nearly equal
```

### 4. Ticker Concentration
- How many different tickers?
- Are top tickers over-represented?
- How diversified is portfolio?

**Example:**
```
Total Tickers: 29 ✓ Excellent
Top 5 Concentration: 38% ⚠️ Slightly high
```

### 5. Price Execution Quality
- Are entry prices reasonable?
- What's the buy/sell spread?
- Any data errors (zero prices)?

**Example:**
```
Avg Buy Price: €72.85
Avg Sell Price: €76.84
Spread: +5.5% ✓ Good execution
Zero Price Orders: 0 ✓ Clean data
```

### 6. Daily Activity Patterns
- What's the daily consistency?
- Are orders spread throughout day?
- Any extreme peaks/valleys?

**Example:**
```
Mean Orders/Day: 3.6
Std Dev: 3.5 ← Problem: High variation (bursty)
```

---

## momentum_cac Analytics Summary

### Order Distribution
```
Total Orders: 229
├─ Buy Orders: 140 (61%)
└─ Sell Orders: 89 (39%)

Buy/Sell Ratio: 1.57x ✓ Balanced
```

### Position Sizing Report
```
Average Buy Size: 36.58 shares
Average Sell Size: 56.52 shares
Range: 3 - 1,470 shares ❌ HUGE variance!

Size Consistency: 0.0% ❌ CRITICAL
→ Problem: position_size formula not applied consistently
→ Recommendation: Implement fixed sizing with constraints
```

### Timing Report
```
Avg Orders/Day: 3.6 orders
Peak Orders/Day: 23 orders ⚠️ Spike
Min Orders/Day: 1 order

Daily Std Dev: 3.5 ⚠️ High (bursty)
Peak Hour: 14:00 (2 PM) - Concentrated

→ Problem: Orders clustered at specific time
→ Recommendation: Spread watchlist updates throughout day
```

### Order Balance Report
```
Total Buy Quantity: 5,121 shares
Total Sell Quantity: 5,030 shares
Imbalance Ratio: 1.02x ✓ EXCELLENT

Avg Buy Price: €72.85
Avg Sell Price: €76.84
Spread: +5.5% ✓ Good execution
```

### Ticker Concentration Report
```
Total Tickers: 29 ✓ Excellent diversification

Most Active:
  1. MT.AS (ArcelorMittal): 21 orders (9%)
  2. STMPA.PA (STMicro): 18 orders (8%)
  3. TTE.PA (TotalEnergies): 17 orders (7%)
  4. GLE.PA (Soc.Gen): 16 orders (7%)
  5. ENGI.PA (Engie): 15 orders (7%)
  ──────────────────────────────────
     Top 5 Total: 87 orders (38%) ⚠️ Slightly concentrated
```

### Price Quality Report
```
Price Range: €2.05 - €336.60 (167x ratio)
├─ Low prices: SAF.PA (€2-3)
└─ High prices: VIV.PA (€330+)

Zero Price Orders: 0 ✓ Perfect data quality
```

---

## Recommendations Generated

### HIGH PRIORITY

**1. Inconsistent Position Sizing**

Problem:
- Position sizes vary from 3 to 1,470 shares
- Size Consistency: 0.0% (should be >75%)
- Indicates formula not being applied correctly

Likely Cause:
```yaml
position_size: 1000 / data["close"]

High-price stock (€300):   1000 ÷ 300 = 3 shares
Low-price stock (€0.68):   1000 ÷ 0.68 = 1,470 shares
```

Impact:
- Unpredictable capital per trade
- Risk management impossible
- Position tracking difficult

Solution:
```yaml
position_size: max(20, min(200, 1000 / data["close"]))
# Now: 20-200 shares range, consistent sizing
```

---

## Key Metrics Explained

### Size Consistency
**What it is:** Percentage of consistent order sizing (0-100%)
**Good value:** > 75%
**Your value:** 0.0%
**Meaning:** All orders different sizes (very bad)

### Buy/Sell Ratio  
**What it is:** Buy orders divided by sell orders
**Good value:** 0.8 - 1.5x
**Your value:** 1.57x
**Meaning:** 57% more buys than sells (acceptable)

### Imbalance Ratio
**What it is:** Total buy quantity / total sell quantity
**Good value:** 0.8 - 1.5x
**Your value:** 1.02x
**Meaning:** Nearly perfect balance (excellent!)

### Ticker Concentration
**What it is:** % of orders from top 5 tickers
**Good value:** < 30%
**Your value:** 38%
**Meaning:** Slightly concentrated (monitor)

### Daily Std Dev vs Mean
**What it is:** Consistency of daily order counts
**Good value:** Std Dev < 0.5 × Mean
**Your value:** Std Dev 3.5 ≈ Mean 3.6 (ratio 97%)
**Meaning:** Highly inconsistent (bursty)

---

## Issues and Solutions

### Issue #1: Position Sizing Inconsistency

**Status:** ⚠️ CRITICAL

**What's Wrong:**
- Orders range from 3 to 1,470 shares
- No consistency (0%)
- Makes position tracking impossible

**Why It Matters:**
- Risk per trade is unpredictable
- Capital allocation uneven
- Hard to manage total exposure

**How to Fix:**
Option A - Capped formula:
```yaml
position_size: max(20, min(200, 1000 / data["close"]))
```

Option B - Fixed shares:
```yaml
position_size: 50  # Always 50 shares
```

Option C - Dollar-based:
```yaml
position_size: max(10, min(200, 1000 / data["close"]))
```

**Expected Result:**
- Consistency: 0% → 75%+
- More predictable trading
- Better risk management

---

### Issue #2: Bursty Order Generation

**Status:** ⚠️ HIGH

**What's Wrong:**
- Peak 23 orders in one day
- Average 3.6 orders/day
- Std Dev = 3.5 (nearly equal to mean)
- Orders concentrated at 2 PM

**Why It Matters:**
- Multiple orders → slippage
- Timing bias concentrated at 2 PM
- System can't handle spikes
- Execution quality suffers

**How to Fix:**

Current (problematic):
```yaml
scheduler:
  cron: "0 14 * * 0-4"  # Only 2 PM
```

Fixed (spread out):
```yaml
scheduler:
  - cron: "30 9 * * 0-4"   # 9:30 AM
  - cron: "30 12 * * 0-4"  # 12:30 PM
  - cron: "30 15 * * 0-4"  # 3:30 PM
  - cron: "30 17 * * 0-4"  # 5:30 PM
```

**Expected Result:**
- Peak reduced from 23 to ~6 orders/day
- Std Dev reduced significantly
- More steady order flow
- Better execution

---

### Issue #3: Ticker Concentration (Optional)

**Status:** ⚠️ MEDIUM

**What's Wrong:**
- Top 5 tickers = 38% of orders
- Should be < 30% for balance

**Why It Matters:**
- Sector concentration risk
- Over-exposure to top performers
- If top 5 drop, strategy underperforms

**How to Fix:**
Monitor quarterly:
```
Q1: 38% concentrated → OK (monitor)
Q2: 42% concentrated → Adjust
Q3: 35% concentrated → Back on track
```

If exceeds 40%, adjust:
- Reduce entry confirmation for top tickers
- Increase entry thresholds for top tickers
- Expand watchlist diversification

---

## Action Plan

### Step 1: Fix Position Sizing (TODAY)

Update strategy config:
```yaml
entry:
  parameters:
    position_size:
      formula: max(20, min(200, 1000 / data["close"]))
      description: Fixed capital, 20-200 share range
```

Expected improvement:
- Consistency: 0% → 80%+
- Predictable per-trade capital

### Step 2: Spread Order Generation (THIS WEEK)

Update scheduler:
```yaml
scheduler:
  - cron: "30 9 * * 0-4"
  - cron: "30 12 * * 0-4"
  - cron: "30 15 * * 0-4"
  - cron: "30 17 * * 0-4"
```

Expected improvement:
- Orders/day peak reduced
- More steady execution

### Step 3: Monitor Concentration (ONGOING)

Quarterly review:
- Track top-5 concentration
- Adjust if > 40%
- Rebalance if needed

### Step 4: Re-run Analysis (NEXT MONTH)

Run portfolio analysis again:
```bash
cresus flow run portfolio_analysis momentum_cac --backtest
```

Verify improvements:
- Size consistency increased
- Order timing more steady
- Concentration improved

---

## Analytics Display Reference

When you run the command, you'll see:

```
📊 Portfolio Metrics
├─ Returns, Sharpe ratio, etc.

✓ No issues found!
├─ (Or issues if critical problems detected)

💡 Recommendations (6)
├─ 📊 Performance Recommendations
│  └─ Strategy/signal improvements
└─ 📋 Order Execution Recommendations
   └─ Your orders analytics recommendations
```

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| `orders_analysis_agent.md` | Technical agent details |
| `orders_analytics_interpretation.md` | Deep analysis of momentum_cac |
| `orders_analytics_display.md` | Complete display reference |
| `research_analysis_architecture.md` | Full architecture |
| `portfolio_stats_analyzer.md` | Performance analysis |
| `ANALYSIS_AGENTS_SUMMARY.md` | Quick summary |

---

## FAQ

**Q: What's a good Size Consistency?**
A: > 75% is good. Yours at 0% needs fixing immediately.

**Q: Is my buy/sell ratio OK?**
A: Yes, 1.57x is within healthy range (0.8-2.0x).

**Q: Why are my sizes so different?**
A: Position_size formula divides by price, so high/low prices get vastly different shares.

**Q: What's bursty order generation?**
A: When you place many orders at once instead of spreading throughout day. Yours peaks at 23/day.

**Q: Is 0.0% consistency real?**
A: Yes, it means every single order is different size (3 to 1,470 shares).

**Q: How do I improve timing?**
A: Spread scheduler across multiple times instead of single time slot.

---

## Bottom Line

**Your Strategy Status: B+ (Needs Adjustments)**

✅ **Good:**
- Order balance excellent (1.02x)
- Diversification excellent (29 tickers)
- Execution quality good (+5.5% spread)
- Data quality perfect (no errors)

❌ **Critical Needs Fix:**
- Position sizing consistency (0%)

⚠️ **Should Improve:**
- Order timing (bursty)
- Ticker concentration (38%)

**Action:** Fix position sizing formula and spread orders across day.

---

**Last Updated:** 2026-05-06
**Strategy Analyzed:** momentum_cac
**Backtest Period:** 2026-01-05 to 2026-05-06 (120 days)
**Orders Analyzed:** 229 orders across 29 tickers

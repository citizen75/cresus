# Orders Analytics Display - Complete Reference

## Overview

When you run the portfolio analysis command, the **Orders Analytics** section displays comprehensive data about order execution quality and provides recommendations for improvement.

## Running Orders Analytics

```bash
cresus flow run portfolio_analysis momentum_cac --backtest
```

Output includes:
1. Portfolio Metrics
2. Identified Issues
3. Performance Recommendations
4. **Order Execution Recommendations** ← You are here

---

## Complete Orders Analytics Display

### Order Summary Section

```
═══════════════════════════════════════════════════════════════
Order Summary
═══════════════════════════════════════════════════════════════
Total Orders:                   229
Buy Orders:                     140
Sell Orders:                    89
Buy/Sell Ratio:                 1.57x
```

**What It Shows:**
- **Total Orders**: Complete count of buy + sell orders
- **Buy/Sell Split**: How many of each operation type
- **Buy/Sell Ratio**: Relationship between buy and sell volume
  - 1.57x = 57% more buys than sells
  - Ideal range: 0.5-2.0x
  - Your value: Good (balanced)

---

### Position Sizing Analysis Section

```
═══════════════════════════════════════════════════════════════
Position Sizing Analysis
═══════════════════════════════════════════════════════════════
Average Buy Size:               36.58 shares
Average Sell Size:              56.52 shares
Min Size:                       3.00 shares
Max Size:                       1470.00 shares
Size Std Dev:                   122.10
Size Consistency:              0.0%
Zero Quantity Orders:           0
```

**What Each Metric Means:**

| Metric | Meaning | Good Range | Your Value | Status |
|--------|---------|-----------|-----------|--------|
| **Avg Buy Size** | Average shares per buy order | 10-100 | 36.58 | ✅ |
| **Avg Sell Size** | Average shares per sell order | 10-100 | 56.52 | ✅ |
| **Min Size** | Smallest order | >1 | 3.0 | ✅ |
| **Max Size** | Largest order | <1000 | 1,470 | ⚠️ |
| **Std Dev** | Size variation | <50 | 122.10 | ❌ |
| **Size Consistency** | % of consistent sizing | >75% | 0.0% | ❌ CRITICAL |
| **Zero Quantity** | Orders with 0 shares | 0 | 0 | ✅ |

**Key Findings:**
- Huge variation from 3 to 1,470 shares
- Size Consistency 0% = highly unpredictable sizing
- Indicates position_size formula not being applied correctly

**What This Means for Your Strategy:**
```
Problem: Formula likely divides fixed capital by price
position_size: 1000 / data["close"]

Result:
  High-price stock (€300) → 1000/300 = 3 shares ❌
  Low-price stock (€0.68) → 1000/0.68 = 1,470 shares ⚠️

Impact:
  • Unpredictable capital per trade
  • Risk management impossible
  • Position sizing inconsistent
```

---

### Timing Analysis Section

```
═══════════════════════════════════════════════════════════════
Timing Analysis
═══════════════════════════════════════════════════════════════
Avg Orders Per Day:             3.6
Max Orders Per Day:             23
Min Orders Per Day:             1
Peak Order Hour:                14 (24h format)
Total Trading Days:             64
```

**What Each Metric Means:**

| Metric | Meaning | Good Pattern | Your Value | Status |
|--------|---------|-------------|-----------|--------|
| **Avg/Day** | Daily order average | 2-5 | 3.6 | ✅ |
| **Max/Day** | Highest single day | <10 | 23 | ❌ |
| **Min/Day** | Lowest single day | >0 | 1 | ⚠️ |
| **Peak Hour** | Hour with most orders | Spread out | 14 (2 PM) | ⚠️ |
| **Trading Days** | Days with any orders | >50% of backtest | 64 | ✅ |

**Key Finding: Order Generation is BURSTY**

```
Bursty Pattern (Bad):
Day 1: 23 orders
Day 2: 1 order
Day 3: 5 orders
Day 4: 0 orders
...

Steady Pattern (Good):
Day 1: 3 orders
Day 2: 4 orders
Day 3: 3 orders
Day 4: 4 orders
...
```

Your pattern is bursty (large variance), which causes:
- Slippage when many orders hit market at once
- Timing bias concentrated at 2 PM
- System strain from order spikes

---

### Order Balance Analysis Section

```
═══════════════════════════════════════════════════════════════
Order Balance Analysis
═══════════════════════════════════════════════════════════════
Total Buy Quantity:             5121 shares
Total Sell Quantity:            5030 shares
Total Buy Value:                $129353.35
Total Sell Value:               $121627.03
Imbalance Ratio:               1.02x
```

**What Each Metric Means:**

| Metric | Meaning | Good Value | Your Value | Status |
|--------|---------|-----------|-----------|--------|
| **Buy Qty** | Total shares bought | Any | 5,121 | ℹ️ |
| **Sell Qty** | Total shares sold | Near buy qty | 5,030 | ✅ |
| **Buy Value** | $ spent on buys | Any | $129,353 | ℹ️ |
| **Sell Value** | $ received from sells | Near buy value | $121,627 | ✅ |
| **Imbalance** | Qty ratio buy/sell | 0.8-1.5x | 1.02x | ✅ EXCELLENT |

**Key Finding: BALANCED TRADING**

- Buy and sell quantities nearly equal (5,121 vs 5,030)
- Imbalance ratio 1.02x is nearly perfect
- Indicates strategy properly exits positions
- NOT stuck in long or short bias

**Positive Insight:**
- Average buy price: $72.85
- Average sell price: $76.84
- **5.5% profit on average trade** ✅

---

### Ticker Concentration Section

```
═══════════════════════════════════════════════════════════════
Ticker Concentration
═══════════════════════════════════════════════════════════════
Total Tickers Traded:           29
Most Active Tickers:
  • MT.AS      -  21 orders
  • STMPA.PA   -  18 orders
  • TTE.PA     -  17 orders
  • GLE.PA     -  16 orders
  • ENGI.PA    -  15 orders
```

**What This Means:**

| Metric | Meaning | Good Value | Your Value | Status |
|--------|---------|-----------|-----------|--------|
| **Total Tickers** | How many different stocks | 20+ | 29 | ✅ EXCELLENT |
| **Top 1 (MT.AS)** | Largest share | <15% | 9.2% | ✅ |
| **Top 5 Total** | Top 5 combined | <30% | 38% | ⚠️ Slightly High |

**Key Finding: GOOD DIVERSIFICATION**

✅ Using all 29 CAC40 tickers (excellent diversification)
⚠️ Top 5 = 38% of orders (slightly concentrated)

**What This Means:**
- Not dependent on single stock
- Broad sector exposure
- Some concentration in industrials/energy (MT, STMPA, TTE, ENGI)

**Not Critical** but could improve by:
- Balancing entry conditions across all tickers
- Avoiding overweighting top performers

---

### Price Analysis Section

```
═══════════════════════════════════════════════════════════════
Price Analysis
═══════════════════════════════════════════════════════════════
Average Buy Price:              €72.85
Average Sell Price:             €76.84
Price Range Min:                €2.05
Price Range Max:                €336.60
Zero Price Orders:              0
```

**What This Means:**

| Metric | Meaning | Your Value | Status |
|--------|---------|-----------|--------|
| **Avg Buy** | Entry price | €72.85 | ℹ️ |
| **Avg Sell** | Exit price | €76.84 | ✅ |
| **Buy/Sell Spread** | Profit on timing | +5.5% | ✅ GOOD |
| **Price Range** | Stock price variance | €2-€337 | ℹ️ |
| **Zero Price Orders** | Data errors | 0 | ✅ PERFECT |

**Key Finding: EXCELLENT DATA QUALITY AND TIMING**

- No zero-price orders (clean data)
- Selling 5.5% higher than buying on average
- Indicates entry signals catch bottoms
- Exit signals capture upside

---

### Daily Activity Patterns Section

```
═══════════════════════════════════════════════════════════════
Daily Activity Patterns
═══════════════════════════════════════════════════════════════
Mean Orders/Day:                3.6
Std Dev (Orders/Day):           3.5
Max Orders in Single Day:       23
Min Orders in Single Day:       1
```

**What This Means:**

| Metric | Meaning | Your Value | Interpretation |
|--------|---------|-----------|-----------------|
| **Mean** | Average | 3.6 | Reasonable frequency |
| **Std Dev** | Variation | 3.5 | Very high variation ⚠️ |
| **Std Dev vs Mean** | Consistency | 97% | Highly inconsistent ❌ |
| **Max** | Peak day | 23 | Spike days exist ⚠️ |
| **Min** | Low day | 1 | Some quiet days ⚠️ |

**Analysis:**
- When Std Dev ≈ Mean = Data is **extremely variable**
- Some days 23 orders, some days 1 order
- This is **BURSTY** not **STEADY**

**Why This Matters:**
- Bursty orders cause execution issues
- Steady orders are better (consistent flow)
- Multiple orders at same time → slippage

---

## Order Execution Recommendations

### Recommendation Structure

Each recommendation has:

```
Priority Level (CRITICAL/HIGH/MEDIUM/LOW)
  └─ Recommendation Title (Category)
     └─ Description (What the problem is)
        └─ Suggestion (How to fix it)
```

### Example: Position Sizing Recommendation

```
HIGH PRIORITY

  1. Inconsistent Position Sizing (position_sizing)
     Position sizes vary by 100% (low consistency)
     → Implement fixed position size formula. Check if position_size 
       calculation in entry config matches intended logic.
```

**Breaking It Down:**

| Part | Meaning | Your Issue |
|------|---------|-----------|
| **Priority** | How urgent | HIGH (not critical but important) |
| **Title** | What's wrong | Inconsistent Position Sizing |
| **Category** | Which area | position_sizing |
| **Description** | The problem | Sizes vary 100% |
| **Suggestion** | How to fix | Implement fixed formula |

**How to Fix:**

Current (broken):
```yaml
position_size: 1000 / data["close"]  # Creates sizes 3-1,470
```

Fixed:
```yaml
position_size: max(20, min(200, 1000 / data["close"]))
```

Result:
- Sizes now constrained to 20-200 shares
- Consistency 0% → 80%+
- Predictable risk per trade

---

## Interpreting All Recommendations Together

### Scenario: momentum_cac Strategy

**Findings Summary:**
- ❌ Position sizing: Highly inconsistent (0%)
- ❌ Order timing: Bursty (23 peak, 1 minimum)
- ✅ Order balance: Excellent (1.02x)
- ✅ Diversification: Excellent (29 tickers)
- ✅ Execution quality: Good (+5.5% spread)
- ✅ Data quality: Perfect (no errors)

**Priority Actions:**

1. **Fix Position Sizing** (CRITICAL)
   - Add min/max constraints
   - Achieve 75%+ consistency
   - Standardize capital per trade

2. **Spread Order Generation** (HIGH)
   - Change scheduler to distribute orders
   - Reduce peak from 23 to ~6/day
   - Improve execution consistency

3. **Monitor Concentration** (MEDIUM)
   - Reduce top-5 from 38% to <30%
   - Quarterly review
   - Rebalance if needed

---

## Key Takeaways

### What Good Orders Analytics Look Like

✅ **Position Sizing:**
- Consistency > 75%
- Min/Max range reasonable
- No extreme outliers

✅ **Timing:**
- Std Dev < 2 (steady not bursty)
- Spread across different hours
- Consistent daily volume

✅ **Balance:**
- Buy/Sell ratio 0.8-1.5x
- Buy and sell quantities similar
- No stuck positions

✅ **Concentration:**
- Top 5 < 30% of orders
- 15+ different tickers
- Diversified across portfolio

✅ **Price Quality:**
- No zero-price orders
- Clean data
- Positive buy/sell spread

### What Your Strategy Shows

**Strengths:**
- Good balance and diversification
- Clean data quality
- Good execution timing (5.5% spread)
- Proper exit behavior

**Weaknesses:**
- Critical sizing inconsistency
- Bursty order generation
- Slight ticker concentration

**Overall Rating: B+ (needs adjustments)**

---

## Next Steps

1. **Review** the orders analytics above
2. **Understand** what each section means
3. **Identify** issues requiring attention
4. **Fix** configuration issues (sizing formula, scheduler)
5. **Re-run** analysis to validate improvements
6. **Track** metrics quarterly

---

## Reference Tables

### Position Sizing Grades

| Consistency | Grade | Meaning |
|------------|-------|---------|
| < 25% | F | Extremely variable |
| 25-50% | D | Very inconsistent |
| 50-75% | C | Somewhat consistent |
| 75-90% | B | Good consistency |
| > 90% | A | Excellent consistency |

### Buy/Sell Ratio Assessment

| Ratio | Assessment | Implication |
|-------|-----------|------------|
| < 0.5 | Too many sells | Weak entries |
| 0.5-0.8 | More sells | Exit-biased strategy |
| 0.8-1.2 | Balanced | Well-balanced entries/exits |
| 1.2-1.5 | More buys | Entry-biased strategy |
| 1.5-2.0 | Many more buys | Strong trend following |
| > 2.0 | Excessive buys | Weak exit signals |

### Ticker Concentration Assessment

| Top-5 % | Assessment | Action |
|---------|-----------|--------|
| < 20% | Excellent | No action |
| 20-30% | Good | Monitor |
| 30-40% | Acceptable | Review annually |
| 40-50% | Concentrated | Improve diversification |
| > 50% | Highly concentrated | Urgent adjustment |

---

## Related Documentation

- `orders_analysis_agent.md` - Technical details
- `orders_analytics_interpretation.md` - Deep analysis of momentum_cac
- `research_analysis_architecture.md` - How all agents work together
- `portfolio_stats_analyzer.md` - Performance recommendations

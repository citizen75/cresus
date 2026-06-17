# Setup Instructions for CAC40 Momentum Backtest

## Quick Start (Recommended)

### Option 1: Run Standalone Python Script (No Graphics)

Works on any system with Python 3.7+

```bash
# Navigate to directory
cd ~/dev/cresus/research/aqr

# Run backtest (no dependencies except pandas, numpy, yfinance)
python3 run_backtest.py

# Output files created:
# - backtest_results.csv
# - backtest_detailed.txt
```

**Advantages:**
- ✅ No graphics library issues
- ✅ Fast execution (~2-3 minutes)
- ✅ Exports results to CSV/TXT
- ✅ Works on all systems

### Option 2: Jupyter Notebook with Graphics

Requires matplotlib and seaborn

```bash
# Install requirements (macOS with Homebrew)
brew install matplotlib seaborn

# Or using pipx (recommended)
pipx install matplotlib seaborn

# Or virtual environment (best practice)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start Jupyter
jupyter notebook backtest_cac40.ipynb
```

## Detailed Setup

### Prerequisites

- Python 3.7 or higher
- pip or pipx

### Method 1: Using Virtual Environment (Recommended)

```bash
# Create virtual environment
cd ~/dev/cresus/research/aqr
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backtest
python3 run_backtest.py

# Or start Jupyter
jupyter notebook backtest_cac40.ipynb

# Deactivate when done
deactivate
```

### Method 2: Using pipx (Clean Installation)

```bash
# Install pipx (one time)
brew install pipx

# Install packages
pipx install matplotlib seaborn jupyter numpy pandas yfinance

# Run backtest
python3 run_backtest.py

# Or start Jupyter
jupyter notebook backtest_cac40.ipynb
```

### Method 3: System-wide with Homebrew (macOS)

```bash
# Install dependencies
brew install matplotlib seaborn jupyter

# Run backtest
python3 run_backtest.py
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'matplotlib'"

**Solution 1:** Use virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install matplotlib seaborn
```

**Solution 2:** Use Homebrew
```bash
brew install matplotlib seaborn
```

**Solution 3:** Run standalone script (no graphics needed)
```bash
python3 run_backtest.py  # Works without matplotlib!
```

### Issue: "Externally managed Python environment"

This is a Python 3.11+ safety feature. Use virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: Jupyter kernel not found

```bash
# Activate virtual environment first
source venv/bin/activate

# Install jupyter
pip install jupyter ipykernel

# Start notebook
jupyter notebook
```

## Available Options

### 1. Standalone Python Script ⭐ (RECOMMENDED)

**File:** `run_backtest.py`

```bash
python3 run_backtest.py
```

**Output:**
- Console tables and statistics
- `backtest_results.csv` - All 8 strategies
- `backtest_detailed.txt` - Full analysis

**Pros:**
- Works everywhere
- Fast (~2-3 minutes)
- No graphics library needed
- Simple to run

### 2. Jupyter Notebook with Charts

**File:** `backtest_cac40.ipynb`

```bash
jupyter notebook backtest_cac40.ipynb
```

**Features:**
- 15 interactive cells
- 7 chart types
- Customizable parameters
- Step-by-step analysis

**Requirements:**
- Jupyter
- Matplotlib
- Seaborn
- Plotly

### 3. Python Scripts in Original Directory

Original CAC40 scripts (in ~/dev/cresus-research/):
- `rank_positions_cac40.py` - Weekly momentum ranking
- `rank_by_quality.py` - Quality-based ranking
- `backtest_cac40.py` - Full comparison backtest

## File Organization

```
~/dev/cresus/research/aqr/
├── backtest_cac40.ipynb          # Jupyter notebook (14 MB source)
├── run_backtest.py               # Standalone Python script
├── requirements.txt              # Python dependencies
├── SETUP_INSTRUCTIONS.md         # This file
├── README.md                      # Usage guide
├── backtest_results.csv           # Output: All strategies
└── backtest_detailed.txt          # Output: Detailed analysis
```

## Running the Backtest

### Quickest Method (1 command, 2-3 minutes)

```bash
cd ~/dev/cresus/research/aqr && python3 run_backtest.py
```

### With Visualization (5-10 minutes)

```bash
cd ~/dev/cresus/research/aqr
jupyter notebook backtest_cac40.ipynb
# In Jupyter: Kernel → Restart & Run All
```

### With Virtual Environment (Clean, Recommended)

```bash
cd ~/dev/cresus/research/aqr
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 run_backtest.py
```

## Expected Output

### Console Output
```
╔════════════════════════════════════════════╗
║ CAC40 MOMENTUM STRATEGY BACKTEST (2010-2026)║
╚════════════════════════════════════════════╝

📊 Configuration:
  Period: 16y
  Stocks: 40
  Rebalancing: Every 5 days
  Transaction Costs: 10 bps

...

╔════════════════════════════════════════════╗
║ BACKTEST RESULTS (Weekly Rebalancing)       ║
╠════════════════════════════════════════════╣

Top 5 (1-month)      131.19%    5.90   -16.89%
Top 5 (3-month)       79.26%    3.80   -22.13%
...

✅ BACKTEST COMPLETE
```

### CSV Output (`backtest_results.csv`)
```
Strategy,Annual Return,Volatility,Sharpe,Max DD,Win Rate
Top 5 (1-month),1.3119,0.2224,5.90,-0.1689,0.6683
Top 5 (3-month),0.7926,0.2083,3.80,-0.2213,0.6029
...
```

### Detailed Output (`backtest_detailed.txt`)
- Full strategy metrics
- Monthly statistics
- Best/worst months
- Win rates

## Next Steps

1. ✅ Run backtest: `python3 run_backtest.py`
2. ✅ Review results: `backtest_results.csv`
3. ✅ Export charts: `jupyter notebook backtest_cac40.ipynb`
4. ✅ Deploy strategy: Use `rank_positions_cac40.py` weekly

## Support

### Documentation
- `README.md` - Usage guide
- `backtest_detailed.txt` - Results analysis
- Original guides in `~/dev/cresus-research/src/alpha-signals/cac40/`

### Original Repository

```
~/dev/cresus-research/src/alpha-signals/cac40/
├── backtest_cac40.py
├── rank_positions_cac40.py
├── rank_by_quality.py
├── config_cac40.yml
└── *.md (detailed guides)
```

## Command Cheat Sheet

```bash
# Quick test (30 seconds)
cd ~/dev/cresus/research/aqr && python3 -c "import pandas, yfinance; print('✅ Ready!')"

# Run backtest (2-3 minutes)
python3 run_backtest.py

# View results
cat backtest_results.csv

# Start notebook
jupyter notebook backtest_cac40.ipynb

# Check requirements
cat requirements.txt

# Create virtual environment
python3 -m venv venv && source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

**Last Updated:** 2026-06-17
**Status:** ✅ Ready to use
**Tested On:** Python 3.9, macOS

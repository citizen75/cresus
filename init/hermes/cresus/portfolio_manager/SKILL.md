---
name: cresus/portfolio_manager
description: "View Cresus portfolio positions, metrics, and asset allocation"
version: 1.0.0
author: Cresus
license: MIT
metadata:
  hermes:
    tags: [Portfolio, Finance, Investments, PEA, BNP]
    category: finance
prerequisites:
  commands: [cresus]
tools:
  - id: portfolio_positions
    description: "Get portfolio positions for a specific portfolio"
    command: "{{skill_dir}}/run_tool.sh positions {{portfolio}}"
    input:
      portfolio: "Portfolio name (PEA, BNP, etc)"
  - id: portfolio_list
    description: "List all available portfolios"
    command: "{{skill_dir}}/run_tool.sh list"
  - id: portfolio_metrics
    description: "Get portfolio performance metrics"
    command: "{{skill_dir}}/run_tool.sh metrics {{portfolio}}"
    input:
      portfolio: "Portfolio name"
  - id: portfolio_allocation
    description: "Get portfolio asset allocation"
    command: "{{skill_dir}}/run_tool.sh allocation {{portfolio}}"
    input:
      portfolio: "Portfolio name"
---

# Cresus Portfolio Manager

View and manage your Cresus portfolio positions, performance metrics, and asset allocation.

## What This Skill Does

Retrieves your portfolio data from Cresus via CLI commands:
- **Positions**: List all holdings with quantities, prices, and valuations
- **Metrics**: Performance metrics including Sharpe ratio, drawdown, profit factor
- **Allocation**: Asset allocation breakdown by ticker
- **List**: View all available portfolios

## When to Use

- User asks to see portfolio positions or holdings
- User wants to check portfolio performance metrics
- User asks about asset allocation
- User wants to list available portfolios (PEA, BNP, test, etc.)

## How It Works

```bash
cresus portfolio positions PEA      # View PEA holdings
cresus portfolio metrics PEA        # Get performance metrics
cresus portfolio allocation PEA     # View allocation breakdown
cresus portfolio list               # List all portfolios
```

All commands use `--mcp` flag for JSON output that's properly formatted.

## Available Portfolios

- **PEA** - French tax-advantaged investment account
- **BNP** - BNP Paribas real portfolio
- **test** - Test/demo portfolio
- **_global** - Global paper portfolio
- Strategy portfolios: etf_pea_trend, cac_trend, nasdaq_100_trend

## Example Output

```
7 positions totaling ~€8,925:
  - MC.PA (LVMH): 2 @ €512.30 = €1,024.60
  - ATO.PA (Atos): 25 @ €41.40 = €1,035.00
  - TTE.PA (TotalEnergies): 17 @ €50.84 = €864.28
  - ASML.AS (ASML): 6 @ €610.10 = €3,660.60
  - PUB.PA (Publicis): 11 @ €84.12 = €925.32
  - LR.PA (Legrand): 6 @ €66.93 = €401.58
  - RI.PA (Pernod Ricard): 10 @ €101.40 = €1,014.00
```

## Prerequisites

- Cresus CLI installed and configured
- Valid portfolio data in Cresus system
- Access to `cresus` command in PATH

## Related Skills

- portfolio_analyzer - Detailed portfolio analysis
- performance_analyzer - Performance metrics and comparisons

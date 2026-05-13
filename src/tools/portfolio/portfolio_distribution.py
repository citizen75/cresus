"""Portfolio return distribution analysis.

Analyzes transaction returns and creates a decile-based distribution
showing trade counts and cumulative P&L for each return percentile.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger

from .journal import Journal


class PortfolioDistribution:
    """Calculate portfolio return distribution."""

    def __init__(self, portfolio_name: str, context: Optional[Dict[str, Any]] = None):
        """Initialize portfolio distribution calculator.

        Args:
            portfolio_name: Name of the portfolio
            context: Optional context dict (for backtest sandboxing)
        """
        self.portfolio_name = portfolio_name
        self.journal = Journal(portfolio_name, context=context)

    def calculate(self) -> Dict[str, Any]:
        """Calculate return distribution by deciles.

        Analyzes closed trades and groups them into 10 percentile buckets (deciles),
        showing trade counts and cumulative P&L for each bucket.

        Returns:
            Dict with distribution data: deciles, trade_counts, pnl_values, statistics
        """
        logger.info(f"Calculating portfolio distribution for {self.portfolio_name}")

        # Load journal
        df = self.journal.load_df()
        if df.empty:
            logger.warning(f"No journal found for {self.portfolio_name}")
            return {
                "status": "error",
                "message": f"No journal found for {self.portfolio_name}",
            }

        # Calculate returns for each trade
        # Group by ticker and operation to match buy/sell pairs
        returns = []
        positions = {}  # Track open positions: {ticker: [(buy_price, quantity, fees, date, metadata), ...]}

        for _, row in df.iterrows():
            ticker = str(row.get("ticker", "")).strip().upper()
            operation = str(row.get("operation", "")).upper()
            quantity = float(row.get("quantity", 0))
            price = float(row.get("price", 0))
            fees = float(row.get("fees", 0))
            date = row.get("date", "")
            metadata = row.get("metadata", "")

            if operation == "BUY":
                if ticker not in positions:
                    positions[ticker] = []
                positions[ticker].append({
                    "price": price,
                    "quantity": quantity,
                    "fees": fees,
                    "date": date,
                    "metadata": metadata,
                })
            elif operation == "SELL" and ticker in positions:
                # Match with oldest buy (FIFO)
                sell_pnl = 0
                remaining_qty = quantity

                while remaining_qty > 0 and positions[ticker]:
                    buy = positions[ticker].pop(0)
                    matched_qty = min(remaining_qty, buy["quantity"])

                    # Calculate P&L for this matched lot
                    gross_pnl = matched_qty * (price - buy["price"])
                    # Prorate buy fees across matched quantity
                    buy_fee_portion = buy["fees"] * (matched_qty / buy["quantity"])
                    # Prorate sell fees across quantity
                    sell_fee_portion = fees * (matched_qty / quantity)

                    net_pnl = gross_pnl - buy_fee_portion - sell_fee_portion
                    cost_basis = matched_qty * buy["price"] + buy_fee_portion

                    if cost_basis != 0:
                        return_pct = (net_pnl / cost_basis) * 100
                    else:
                        return_pct = 0

                    returns.append({
                        "ticker": ticker,
                        "quantity": matched_qty,
                        "cost_basis": cost_basis,
                        "pnl": net_pnl,
                        "return_pct": return_pct,
                        "entry_date": buy["date"],
                        "exit_date": date,
                        "entry_metadata": buy["metadata"],
                        "exit_metadata": metadata,
                    })

                    remaining_qty -= matched_qty
                    sell_pnl += net_pnl

        if not returns:
            logger.warning("No closed trades found in journal")
            return {
                "status": "success",
                "portfolio_name": self.portfolio_name,
                "distribution": [],
                "statistics": {
                    "total_trades": 0,
                    "total_pnl": 0,
                    "win_rate": 0,
                    "avg_return": 0,
                    "median_return": 0,
                },
            }

        # Create DataFrame of returns
        df_returns = pd.DataFrame(returns)

        # Calculate 4% return bins
        # Determine the range and create fixed-width bins
        min_return = df_returns["return_pct"].min()
        max_return = df_returns["return_pct"].max()

        # Create bins with 4% width
        bin_size = 4
        min_bin = (int(min_return / bin_size) - 1) * bin_size  # Round down to nearest 4%
        max_bin = (int(max_return / bin_size) + 1) * bin_size  # Round up to nearest 4%

        bins = np.arange(min_bin, max_bin + bin_size, bin_size)
        df_returns["bin"] = pd.cut(
            df_returns["return_pct"],
            bins=bins,
            labels=False,
            include_lowest=True
        )

        # Group by bin and calculate statistics
        grouped = df_returns.groupby("bin", sort=True).agg({
            "return_pct": ["min", "max", "count"],
            "pnl": "sum",
        }).reset_index()

        grouped.columns = ["bin", "return_min", "return_max", "trade_count", "cumulative_pnl"]

        # Calculate cumulative metrics
        cumulative_pnl = []
        cumulative_count = []
        running_pnl = 0
        running_count = 0

        for _, row in grouped.iterrows():
            running_pnl += row["cumulative_pnl"]
            running_count += int(row["trade_count"])
            cumulative_pnl.append(running_pnl)
            cumulative_count.append(running_count)

        grouped["cumulative_pnl_total"] = cumulative_pnl
        grouped["cumulative_count"] = cumulative_count

        # Format for response
        distribution = []
        for _, row in grouped.iterrows():
            # Create clean bin labels showing the 5% range
            bin_label = f"{row['return_min']:.0f}% to {row['return_max']:.0f}%"
            distribution.append({
                "bin_label": bin_label,
                "return_range": bin_label,
                "return_min": float(row["return_min"]),
                "return_max": float(row["return_max"]),
                "trade_count": int(row["trade_count"]),
                "cumulative_pnl": float(row["cumulative_pnl"]),
                "cumulative_pnl_total": float(row["cumulative_pnl_total"]),
                "cumulative_count": int(row["cumulative_count"]),
            })

        # Calculate overall statistics
        total_pnl = df_returns["pnl"].sum()
        total_trades = len(df_returns)
        winning_trades = len(df_returns[df_returns["pnl"] > 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        statistics = {
            "total_trades": total_trades,
            "total_pnl": float(total_pnl),
            "win_rate": float(win_rate),
            "avg_return": float(df_returns["return_pct"].mean()),
            "median_return": float(df_returns["return_pct"].median()),
            "min_return": float(df_returns["return_pct"].min()),
            "max_return": float(df_returns["return_pct"].max()),
            "std_return": float(df_returns["return_pct"].std()),
        }

        logger.info(f"Calculated distribution with {total_trades} trades across {len(distribution)} bins (4% steps)")

        return {
            "status": "success",
            "portfolio_name": self.portfolio_name,
            "distribution": distribution,
            "statistics": statistics,
            "trades": returns,  # Include closed trades with metadata
        }

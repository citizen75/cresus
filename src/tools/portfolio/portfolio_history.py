"""Portfolio daily history calculation.

Replays journal transactions to compute portfolio value for each calendar day
since first transaction, using historical closing prices.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from .journal import Journal
from tools.data import DataHistory


class PortfolioHistory:
    """Calculate daily portfolio value history."""

    def __init__(self, portfolio_name: str, initial_capital: Optional[float] = None, context: Optional[Dict[str, Any]] = None):
        """Initialize portfolio history calculator.

        Args:
            portfolio_name: Name of the portfolio
            initial_capital: Starting cash amount. If None, loads from config.
            context: Optional context dict (for backtest sandboxing)
        """
        self.portfolio_name = portfolio_name
        self.journal = Journal(portfolio_name, context=context)
        self.initial_capital = initial_capital

    def calculate(self, recalculate: bool = False) -> Dict[str, Any]:
        """Calculate daily portfolio history.

        Args:
            recalculate: If True, recalculate even if cached

        Returns:
            Dict with history data and metadata
        """
        logger.info(f"Calculating portfolio history for {self.portfolio_name}")

        # Load journal
        df = self.journal.load_df()
        if df.empty:
            logger.warning(f"No journal found for {self.portfolio_name}")
            return {
                "status": "error",
                "message": f"No journal found for {self.portfolio_name}",
            }

        # Convert created_at to datetime, handling NaT values
        # Use format with optional microseconds to handle mixed formats
        df["created_at"] = pd.to_datetime(
            df["created_at"],
            format="mixed",
            errors="coerce"
        )
        df_valid = df[df["created_at"].notna()].copy()

        if df_valid.empty:
            logger.warning("No valid dates in journal")
            return {"status": "error", "message": "No valid dates in journal"}

        # Normalize created_at to date-only (00:00:00) for date-based comparisons
        df_valid["created_at"] = df_valid["created_at"].dt.normalize()

        # Get date range
        first_tx_date = df_valid["created_at"].min()
        last_tx_date = df_valid["created_at"].max()

        if pd.isna(first_tx_date) or pd.isna(last_tx_date):
            logger.warning("Invalid dates in journal")
            return {"status": "error", "message": "Invalid dates in journal"}

        first_tx_date = pd.Timestamp(first_tx_date)
        last_tx_date = pd.Timestamp(last_tx_date)

        logger.info(f"Date range: {first_tx_date} to {last_tx_date}")

        # Collect unique tickers (excluding CASH)
        tickers = set()
        for _, row in df_valid.iterrows():
            ticker = str(row.get("ticker", "")).strip().upper()
            if ticker and ticker != "CASH":
                tickers.add(ticker)

        # Preload history data for all tickers
        logger.info(f"Preloading history for {len(tickers)} tickers")
        ticker_history = {}
        for ticker in tickers:
            try:
                history_store = DataHistory(ticker)
                df_all = history_store.get_all()

                # If no cached data, try to fetch
                if df_all.empty:
                    logger.info(f"  No cache for {ticker}, fetching from yfinance...")
                    result = history_store.fetch(start_date=first_tx_date.strftime("%Y-%m-%d"))
                    if result.get("status") == "success":
                        df_all = history_store.get_all()
                    else:
                        logger.warning(f"Failed to fetch history for {ticker}: {result.get('message', '')}")

                if df_all is not None and not df_all.empty:
                    ticker_history[ticker] = df_all
                    logger.debug(f"  Loaded {len(df_all)} rows for {ticker}")
                else:
                    logger.warning(f"No history data found for {ticker}")
            except Exception as e:
                logger.warning(f"Error loading history for {ticker}: {e}")
                continue

        # Calculate daily values
        daily_history = []
        current_date = first_tx_date

        while current_date <= last_tx_date:
            # Replay all transactions up to this date (inclusive)
            rows_up_to = df_valid[df_valid["created_at"] <= current_date]

            if rows_up_to.empty:
                current_date += timedelta(days=1)
                continue

            # Calculate positions and cash
            positions = {}
            cash = self.initial_capital if self.initial_capital else 0

            for _, row in rows_up_to.iterrows():
                ticker = str(row.get("ticker", "")).strip().upper()
                operation = str(row.get("operation", "")).upper()
                quantity = float(row.get("quantity", 0))
                price = float(row.get("price", 0))
                fees = float(row.get("fees", 0))

                if operation == "CASH":
                    # CASH: quantity is the amount (positive=deposit, negative=withdrawal)
                    cash += quantity
                elif operation == "BUY":
                    if ticker not in positions:
                        positions[ticker] = 0
                    positions[ticker] += quantity
                    cash -= (quantity * price + fees)
                elif operation == "SELL":
                    if ticker not in positions:
                        positions[ticker] = 0
                    positions[ticker] -= quantity
                    cash += (quantity * price - fees)

            # Calculate portfolio value at this date
            portfolio_value = cash
            positions_value = 0

            for ticker, quantity in positions.items():
                if quantity > 0 and ticker in ticker_history:
                    # Get price on or before this date
                    df_ticker = ticker_history[ticker].copy()
                    df_ticker["timestamp"] = pd.to_datetime(df_ticker["timestamp"], errors="coerce")
                    # Remove timezone info if present for comparison
                    if df_ticker["timestamp"].dt.tz is not None:
                        df_ticker["timestamp"] = df_ticker["timestamp"].dt.tz_localize(None)
                    prices_before = df_ticker[df_ticker["timestamp"].dt.normalize() <= current_date]

                    if not prices_before.empty:
                        price = float(prices_before.iloc[-1].get("close", 0))
                        value = quantity * price
                        positions_value += value
                        portfolio_value += value

            daily_history.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "value": round(portfolio_value, 2),
                "positions_value": round(positions_value, 2),
                "cash": round(cash, 2),
            })

            current_date += timedelta(days=1)

        logger.info(f"Calculated {len(daily_history)} daily values")

        return {
            "portfolio_name": self.portfolio_name,
            "history": daily_history,
            "status": "success",
        }

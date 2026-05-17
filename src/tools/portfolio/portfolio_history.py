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
from tools.data.manager import DataManager


class PortfolioHistory:
    """Calculate daily portfolio value history."""

    def __init__(self, portfolio_name: str, initial_capital: Optional[float] = None, context: Optional[Dict[str, Any]] = None, data_manager: Optional[DataManager] = None):
        """Initialize portfolio history calculator.

        Args:
            portfolio_name: Name of the portfolio
            initial_capital: Starting cash amount. If None, loads from config.
            context: Optional context dict (for backtest sandboxing)
            data_manager: Optional DataManager for centralized data fetching
        """
        self.portfolio_name = portfolio_name
        self.journal = Journal(portfolio_name, context=context)
        self.initial_capital = initial_capital
        self.data_manager = data_manager or DataManager(Path.cwd())

    def calculate(self, recalculate: bool = False, use_cache_only: bool = False) -> Dict[str, Any]:
        """Calculate daily portfolio history.

        Args:
            recalculate: If True, recalculate even if cached
            use_cache_only: If True, only use cached data and skip fetching for invalid tickers

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
        logger.info(f"Preloading history for {len(tickers)} tickers (cache_only={use_cache_only})")
        ticker_history = {}
        failed_tickers = []

        from tools.data import DataHistory

        for ticker in tickers:
            dh = DataHistory(ticker)

            if use_cache_only:
                # Only use cached data - don't fetch
                df_all = dh.get_all()
                if df_all is not None and not df_all.empty:
                    ticker_history[ticker] = df_all
                    logger.debug(f"  Loaded {len(df_all)} rows for {ticker} (cached)")
                else:
                    logger.warning(f"No cached history for {ticker}")
                    failed_tickers.append(ticker)
            else:
                # Fetch fresh data via DataManager
                result = self.data_manager.fetch_history(ticker, start_date=first_tx_date.strftime("%Y-%m-%d"))

                if result.get("status") == "success":
                    df_all = dh.get_all()
                    if df_all is not None and not df_all.empty:
                        ticker_history[ticker] = df_all
                        logger.debug(f"  Loaded {len(df_all)} rows for {ticker}")
                    else:
                        logger.warning(f"No history data found for {ticker}")
                        failed_tickers.append(ticker)
                else:
                    logger.warning(f"Failed to fetch history for {ticker}: {result.get('message', '')}")
                    failed_tickers.append(ticker)

        # Calculate daily values efficiently
        # Build position tracking by replaying transactions once (forward pass)
        daily_history = []
        positions = {}  # {ticker: quantity}
        cash = self.initial_capital if self.initial_capital else 0
        peak_value = cash

        # Get all unique transaction dates, starting from oldest transaction
        tx_dates = sorted(df_valid["created_at"].unique())

        if not tx_dates:
            return {"status": "error", "message": "No transactions found"}

        # Cache ticker price lookups
        ticker_price_cache = {}  # {ticker: {date: price}}

        def get_price_on_date(ticker, date):
            """Get price for ticker on or before date."""
            if ticker not in ticker_history:
                return None

            if ticker not in ticker_price_cache:
                ticker_price_cache[ticker] = {}

            if date not in ticker_price_cache[ticker]:
                df_ticker = ticker_history[ticker].copy()
                df_ticker["timestamp"] = pd.to_datetime(df_ticker["timestamp"], errors="coerce")
                if df_ticker["timestamp"].dt.tz is not None:
                    df_ticker["timestamp"] = df_ticker["timestamp"].dt.tz_localize(None)
                prices_before = df_ticker[df_ticker["timestamp"].dt.normalize() <= date]
                if not prices_before.empty:
                    ticker_price_cache[ticker][date] = float(prices_before.iloc[-1].get("close", 0))
                else:
                    ticker_price_cache[ticker][date] = None

            return ticker_price_cache[ticker].get(date)

        # Process each transaction date
        current_date = first_tx_date
        for tx_date in tx_dates:
            # Process all transactions on this date
            rows_on_date = df_valid[df_valid["created_at"] == tx_date]

            for _, row in rows_on_date.iterrows():
                ticker = str(row.get("ticker", "")).strip().upper()
                operation = str(row.get("operation", "")).upper()
                quantity = float(row.get("quantity", 0))
                price = float(row.get("price", 0))
                fees = float(row.get("fees", 0))

                if operation == "CASH":
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

            # Record value at this transaction date
            portfolio_value = cash
            positions_value = 0

            for ticker, quantity in positions.items():
                if quantity > 0:
                    p = get_price_on_date(ticker, tx_date)
                    if p:
                        positions_value += quantity * p
                        portfolio_value += quantity * p

            if portfolio_value > peak_value:
                peak_value = portfolio_value

            drawdown = ((portfolio_value - peak_value) / peak_value * 100) if peak_value > 0 else 0

            daily_history.append({
                "date": tx_date.strftime("%Y-%m-%d"),
                "value": round(portfolio_value, 2),
                "positions_value": round(positions_value, 2),
                "cash": round(cash, 2),
                "drawdown_pct": round(drawdown, 2),
            })

        logger.info(f"Calculated {len(daily_history)} daily values")

        result = {
            "portfolio_name": self.portfolio_name,
            "history": daily_history,
            "status": "success",
            "tickers_loaded": len(ticker_history),
            "tickers_total": len(tickers),
        }

        if failed_tickers:
            result["failed_tickers"] = failed_tickers
            logger.warning(f"Failed to fetch data for {len(failed_tickers)} tickers: {failed_tickers}")

        return result

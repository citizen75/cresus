"""Shared helpers for order/exit execution agents (TradingBroker and its sub-agents).

Consolidates logic that was previously copy-pasted across multiple execution
sub-agents: broker reconstruction from journal history, market-row-to-metadata
conversion, day-data price lookups, and the fixed intraday execution timestamp.
"""

from typing import Any, Dict, Optional
from datetime import date as date_type
import pandas as pd

from .broker import PaperBroker
from .journal import Journal

EXECUTION_TIME = "14:00:00.000000"


def trading_datetime(trading_date: date_type) -> str:
    """ISO timestamp for a trading date, fixed at the standard intraday execution time."""
    return f"{trading_date.isoformat()}T{EXECUTION_TIME}"


def get_price(day_data: Dict[str, Any], ticker: str, field: str) -> Optional[float]:
    """Get a single OHLC field (open/high/low/close) for ticker from pre-sliced day data.

    Args:
        day_data: Pre-sliced market data {ticker: row}
        ticker: Ticker symbol
        field: Row field to read (e.g. "open", "close", "low", "high")

    Returns:
        Price as float, or None if unavailable
    """
    if ticker not in day_data:
        return None

    row = day_data[ticker]
    try:
        value = row.get(field) if field in row else None
        return float(value) if value is not None else None
    except (ValueError, TypeError, AttributeError):
        return None


def row_to_metadata(row: Any) -> Optional[Dict[str, Any]]:
    """Convert a market data row (pandas Series or dict) into a JSON-safe metadata dict.

    Returns None for missing/empty rows so callers can pass it straight through
    to Journal.add_transaction(metadata=...).
    """
    if row is None:
        return None

    try:
        if isinstance(row, pd.Series):
            data = row.to_dict()
        elif isinstance(row, dict):
            data = dict(row)
        else:
            data = dict(row)
    except Exception:
        return None

    if not data:
        return None

    metadata: Dict[str, Any] = {}
    for key, value in data.items():
        try:
            if value is None or pd.isna(value):
                metadata[key] = None
            elif hasattr(value, "isoformat"):
                metadata[key] = value.isoformat()
            elif isinstance(value, (int, float)):
                metadata[key] = float(value)
            else:
                metadata[key] = str(value)
        except (TypeError, ValueError):
            metadata[key] = value

    return metadata or None


def broker_from_journal(journal: Journal, logger: Any = None) -> PaperBroker:
    """Build a PaperBroker pre-loaded with open positions reconstructed from the journal.

    SELL/exit execution needs real positions to validate against, not the broker's
    empty in-memory state, so callers replay BUY transactions to seed the broker.

    Args:
        journal: Journal with transaction history
        logger: Optional logger for debug output on failure

    Returns:
        PaperBroker with positions loaded from journal
    """
    broker = PaperBroker()

    try:
        journal_df = journal.load_df()
        if journal_df.empty or "operation" not in journal_df.columns:
            return broker

        buy_transactions = journal_df[journal_df["operation"].str.upper() == "BUY"]
        positions: Dict[str, Dict[str, Any]] = {}

        for ticker in buy_transactions["ticker"].unique():
            ticker_buys = buy_transactions[buy_transactions["ticker"] == ticker]
            total_quantity = 0.0
            weighted_price = 0.0

            for _, transaction in ticker_buys.iterrows():
                qty = float(transaction.get("quantity", 0))
                price = float(transaction.get("price", 0))
                total_quantity += qty
                weighted_price += qty * price

            if total_quantity > 0:
                positions[ticker] = {
                    "ticker": ticker,
                    "quantity": int(total_quantity),
                    "entry_price": weighted_price / total_quantity,
                    "current_price": weighted_price / total_quantity,
                    "stop_loss": None,
                    "target_price": None,
                    "strategy_id": "transact",
                }

        broker.positions = positions
    except Exception as e:
        if logger is not None:
            logger.debug(f"Could not load positions from journal: {e}")

    return broker

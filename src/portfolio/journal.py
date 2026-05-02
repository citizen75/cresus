"""Trading journal with transaction-based CSV persistence."""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import pandas as pd
import os
import uuid


class Journal:
    """Transaction-based trading journal - CSV store for individual transactions."""

    BASE_COLUMNS = [
        "id", "created_at", "operation", "ticker", "quantity",
        "price", "amount", "fees", "status", "status_at", "notes"
    ]

    def __init__(self, name: str = "default"):
        project_root = Path(os.environ.get("CRESUS_PROJECT_ROOT", os.getcwd()))
        self.filepath = project_root / "db" / "local" / "portfolios" / f"{name}_journal.csv"
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.name = name
        self._ensure_base_structure()

    def _ensure_base_structure(self) -> None:
        """Ensure journal file exists with correct columns."""
        if not self.filepath.exists():
            df = pd.DataFrame(columns=self.BASE_COLUMNS)
            df.to_csv(self.filepath, index=False)

    def load_df(self) -> pd.DataFrame:
        """Load journal as DataFrame."""
        if not self.filepath.exists():
            return pd.DataFrame(columns=self.BASE_COLUMNS)
        return pd.read_csv(self.filepath, dtype=object)

    def save(self, df: pd.DataFrame) -> None:
        """Save DataFrame to CSV."""
        df.to_csv(self.filepath, index=False)

    def add_transaction(self, operation: str, ticker: str, quantity: int, price: float,
                       fees: float = 0, notes: str = "", created_at: str = None) -> str:
        """Add a new transaction to journal.

        Operations: BUY, SELL, CASH (deposit/withdrawal)
        For CASH: ticker should be "CASH", quantity is the amount (positive=deposit, negative=withdrawal)

        Returns the transaction ID.
        """
        df = self.load_df()

        transaction_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        # Use provided created_at or default to now
        tx_created_at = created_at if created_at else now

        operation_upper = operation.upper()

        # Handle CASH operations
        if operation_upper == "CASH":
            # For CASH: quantity is the amount, ticker is always "CASH"
            amount = quantity
            ticker_val = "CASH"
            price_val = 1.0
        else:
            # For BUY/SELL: quantity * price = amount
            amount = quantity * price
            ticker_val = ticker.upper()
            price_val = float(price)

        new_row = {
            "id": transaction_id,
            "created_at": tx_created_at,
            "operation": operation_upper,
            "ticker": ticker_val,
            "quantity": int(quantity),
            "price": price_val,
            "amount": round(amount, 2),
            "fees": float(fees),
            "status": "completed",
            "status_at": now,
            "notes": notes
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        self.save(df)
        return transaction_id

    def get_open_positions(self) -> pd.DataFrame:
        """Calculate open positions from buy/sell transactions."""
        df = self.load_df()
        if df.empty:
            return pd.DataFrame()

        # Convert to proper types
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df["fees"] = pd.to_numeric(df["fees"], errors="coerce")

        positions = {}

        for _, row in df.iterrows():
            if row["status"] != "completed":
                continue

            ticker = row["ticker"]
            operation = row["operation"].upper()

            # Skip CASH operations - they don't create positions
            if operation == "CASH":
                continue

            quantity = row["quantity"]
            price = row["price"]
            fees = row["fees"] if pd.notna(row["fees"]) else 0

            if ticker not in positions:
                positions[ticker] = {
                    "ticker": ticker,
                    "quantity": 0,
                    "total_cost": 0,
                    "fees": 0,
                    "transactions": []
                }

            if operation == "BUY":
                positions[ticker]["quantity"] += quantity
                positions[ticker]["total_cost"] += (quantity * price)
                positions[ticker]["fees"] += fees
            elif operation == "SELL":
                positions[ticker]["quantity"] -= quantity
                positions[ticker]["total_cost"] -= (quantity * price)
                positions[ticker]["fees"] += fees

            positions[ticker]["transactions"].append(row.to_dict())

        # Filter out closed positions
        open_positions = {k: v for k, v in positions.items() if v["quantity"] > 0}

        result = []
        for ticker, data in open_positions.items():
            avg_entry_price = data["total_cost"] / data["quantity"] if data["quantity"] > 0 else 0
            result.append({
                "ticker": ticker,
                "quantity": int(data["quantity"]),
                "avg_entry_price": round(avg_entry_price, 2),
                "entry_fees": round(data["fees"], 2),
            })

        return pd.DataFrame(result)

    def remove_position(self, ticker: str) -> bool:
        """Remove all transactions for a ticker from journal."""
        df = self.load_df()
        if df.empty:
            return False

        df = df[df["ticker"].str.upper() != ticker.upper()]
        self.save(df)
        return True

    def update_position(self, ticker: str, quantity: int, price: float, fees: float = 0) -> bool:
        """Update entry transaction for a position (modify the most recent BUY)."""
        df = self.load_df()
        if df.empty:
            return False

        # Find the most recent BUY transaction for this ticker
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        ticker_buys = df[
            (df["ticker"].str.upper() == ticker.upper()) &
            (df["operation"].str.upper() == "BUY")
        ].sort_values("created_at")

        if ticker_buys.empty:
            return False

        # Update the first (earliest) BUY transaction
        idx = ticker_buys.index[0]
        df.loc[idx, "quantity"] = int(quantity)
        df.loc[idx, "price"] = float(price)
        df.loc[idx, "amount"] = round(quantity * price, 2)
        df.loc[idx, "fees"] = float(fees)
        df.loc[idx, "status_at"] = datetime.now().isoformat()

        self.save(df)
        return True

    def to_transactions(self) -> pd.DataFrame:
        """Return all transactions."""
        return self.load_df().copy()

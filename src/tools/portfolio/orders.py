"""Trading orders with pending/executable order tracking."""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import pandas as pd
import os
import uuid
import json


class Orders:
    """Order management - tracks pending and executable orders separately from executed transactions."""

    BASE_COLUMNS = [
        "id", "created_at", "ticker", "quantity", "entry_price", "limit_price",
        "stop_loss", "take_profit", "trailing_stop_distance", "execution_method", "scale_count",
        "risk_amount", "risk_reward", "status", "metadata"
    ]

    def __init__(self, name: str = "default", context: Optional[Dict[str, Any]] = None):
        project_root = Path(os.environ.get("CRESUS_PROJECT_ROOT", os.getcwd()))
        # Normalize portfolio name to lowercase snake_case
        normalized_name = self._normalize_name(name)

        # Store context for caching
        self.context = context
        self.cache_key = f"_orders_cache_{normalized_name}"

        # Check if running in backtest context
        backtest_dir = None
        if context:
            backtest_dir = context.get("backtest_dir")

        if backtest_dir:
            # Use sandboxed backtest directory
            self.filepath = Path(backtest_dir) / "orders" / f"{normalized_name}_orders.csv"
        else:
            # Use normal directory
            self.filepath = project_root / "db" / "local" / "orders" / f"{normalized_name}_orders.csv"

        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.name = normalized_name
        self._ensure_base_structure()

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize portfolio name to lowercase snake_case.

        Examples:
            "Momentum cac" → "momentum_cac"
            "PEA Gilles" → "pea_gilles"
            "momentum_cac" → "momentum_cac"
        """
        return name.lower().replace(" ", "_")

    def _ensure_base_structure(self) -> None:
        """Ensure orders file exists with correct columns."""
        if not self.filepath.exists():
            df = pd.DataFrame(columns=self.BASE_COLUMNS)
            df.to_csv(self.filepath, index=False, quoting=1, quotechar='"')

    def load_df(self) -> pd.DataFrame:
        """Load orders as DataFrame, using context cache if available."""
        # Check context cache first
        if self.context and self.cache_key in self.context:
            return self.context[self.cache_key].copy()
        
        # Load from file
        if not self.filepath.exists():
            df = pd.DataFrame(columns=self.BASE_COLUMNS)
        else:
            df = pd.read_csv(self.filepath, dtype=object, quotechar='"', quoting=1)
        
        # Cache in context if available
        if self.context is not None:
            self.context[self.cache_key] = df.copy()
        
        return df

    def save(self, df: pd.DataFrame) -> None:
        """Save DataFrame to CSV and update context cache."""
        df.to_csv(self.filepath, index=False, quoting=1, quotechar='"')
        
        # Update context cache
        if self.context is not None:
            self.context[self.cache_key] = df.copy()

    def add_order(self, ticker: str, quantity: int, entry_price: float,
                  stop_loss: Optional[float] = None, take_profit: Optional[float] = None,
                  limit_price: Optional[float] = None,
                  trailing_stop_distance: Optional[float] = None,
                  execution_method: str = "market", scale_count: int = 1,
                  risk_amount: Optional[float] = None, risk_reward: Optional[float] = None,
                  metadata: Optional[Dict[str, Any]] = None,
                  replace_same_day: bool = True,
                  created_at: Optional[str] = None) -> str:
        """Add a new order to orders file.

        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares
            entry_price: Entry price (for reference/analysis)
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            limit_price: Limit price for limit orders (optional, default: entry_price for market)
            trailing_stop_distance: Distance below highest price for trailing stop (optional)
            execution_method: Execution method (market, limit, scale_in)
            scale_count: Number of scale-in levels
            risk_amount: Risk amount in currency
            risk_reward: Risk/reward ratio
            metadata: Additional order metadata (strategy, entry_score, etc)
            replace_same_day: If True, cancel previous pending orders for same ticker on same day
            created_at: Order creation timestamp (optional, default: now)

        Returns:
            Order ID
        """
        df = self.load_df()

        # Ensure DataFrame has the correct columns even if empty
        for col in self.BASE_COLUMNS:
            if col not in df.columns:
                df[col] = None

        # Cancel previous pending orders for same ticker on same day if replace_same_day=True
        if replace_same_day:
            self._cancel_same_day_orders(ticker, df)
            df = self.load_df()  # Reload after cancellation

        order_id = str(uuid.uuid4())[:8]
        now = created_at or datetime.now().isoformat()

        metadata_json = json.dumps(metadata) if metadata else ""

        new_row = {
            "id": order_id,
            "created_at": now,
            "ticker": ticker.upper(),
            "quantity": int(quantity),
            "entry_price": float(entry_price),
            "limit_price": float(limit_price) if limit_price is not None else None,
            "stop_loss": float(stop_loss) if stop_loss is not None else None,
            "take_profit": float(take_profit) if take_profit is not None else None,
            "trailing_stop_distance": float(trailing_stop_distance) if trailing_stop_distance is not None else None,
            "execution_method": execution_method,
            "scale_count": int(scale_count),
            "risk_amount": float(risk_amount) if risk_amount is not None else None,
            "risk_reward": float(risk_reward) if risk_reward is not None else None,
            "status": "pending",
            "metadata": metadata_json,
        }

        import warnings
        new_df = pd.DataFrame([new_row])
        # Suppress FutureWarning about DataFrame concatenation with empty/NA entries
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            df = pd.concat([df, new_df], ignore_index=True)
        self.save(df)
        return order_id

    def _cancel_same_day_orders(self, ticker: str, df: Optional[pd.DataFrame] = None) -> int:
        """Cancel previous pending orders for same ticker on same day.

        Args:
            ticker: Ticker symbol
            df: Optional DataFrame to use (otherwise loads from file)

        Returns:
            Number of orders cancelled
        """
        if df is None:
            df = self.load_df()

        if df.empty:
            return 0

        today = datetime.now().date().isoformat()
        ticker_upper = ticker.upper()

        # Find pending orders for same ticker created today
        mask = (
            (df["ticker"].str.upper() == ticker_upper) &
            (df["status"].str.lower() == "pending") &
            (df["created_at"].str.startswith(today))
        )

        cancelled_count = mask.sum()

        if cancelled_count > 0:
            df.loc[mask, "status"] = "cancelled"
            self.save(df)

        return cancelled_count

    def get_pending_orders(self) -> pd.DataFrame:
        """Get all pending orders."""
        df = self.load_df()
        if df.empty:
            return pd.DataFrame()
        return df[df["status"].str.upper() == "PENDING"].copy()

    def get_all_orders(self) -> pd.DataFrame:
        """Get all orders (pending, executed, cancelled)."""
        return self.load_df().copy()

    def update_order_status(self, order_id: str, status: str) -> bool:
        """Update order status (pending, executed, cancelled).

        Args:
            order_id: Order ID
            status: New status

        Returns:
            True if updated, False if order not found
        """
        df = self.load_df()
        if df.empty:
            return False

        mask = df["id"] == order_id
        if not mask.any():
            return False

        df.loc[mask, "status"] = status.lower()
        self.save(df)
        return True

    def remove_order(self, order_id: str) -> bool:
        """Remove an order (typically pending orders that are cancelled).

        Args:
            order_id: Order ID

        Returns:
            True if removed, False if order not found
        """
        df = self.load_df()
        if df.empty:
            return False

        if order_id not in df["id"].values:
            return False

        df = df[df["id"] != order_id]
        self.save(df)
        return True

    def to_orders(self) -> List[Dict[str, Any]]:
        """Return all orders as list of dicts."""
        df = self.load_df()
        if df.empty:
            return []

        orders = []
        for _, row in df.iterrows():
            # Parse metadata JSON if present
            metadata = {}
            if pd.notna(row.get("metadata")) and str(row.get("metadata")).strip():
                try:
                    metadata = json.loads(str(row.get("metadata")))
                except Exception:
                    pass

            order = {
                "id": str(row.get("id", "")),
                "ticker": str(row.get("ticker", "")),
                "quantity": int(row.get("quantity", 0)),
                "entry_price": float(row.get("entry_price", 0)),
                "stop_loss": float(row.get("stop_loss")) if pd.notna(row.get("stop_loss")) else None,
                "take_profit": float(row.get("take_profit")) if pd.notna(row.get("take_profit")) else None,
                "execution_method": str(row.get("execution_method", "market")),
                "scale_count": int(row.get("scale_count", 1)),
                "risk_amount": float(row.get("risk_amount")) if pd.notna(row.get("risk_amount")) else None,
                "risk_reward": float(row.get("risk_reward")) if pd.notna(row.get("risk_reward")) else None,
                "status": str(row.get("status", "pending")).lower(),
                "created_at": str(row.get("created_at", "")),
                "metadata": metadata,
            }
            orders.append(order)

        return orders

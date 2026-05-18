"""Portfolio manager - orchestrates positions, transactions, and metrics."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import os
import yaml
import json
import pandas as pd
from loguru import logger

from .journal import Journal
from tools.data import Fundamental, DataHistory
from .cache import PortfolioCache
from .portfolio_history import PortfolioHistory
from utils.env import get_db_root, get_config_root


class PortfolioManager:
    """Manage portfolios: positions, transactions, performance."""

    def __init__(
        self,
        portfolios_dir: Optional[Path] = None,
        config_path: Optional[Path] = None,
        orders_dir: Optional[Path] = None,
        in_memory: bool = False,
        context: Optional[Dict[str, Any]] = None,
    ):
        project_root = Path(os.environ.get("CRESUS_PROJECT_ROOT", os.getcwd()))
        self.context = context or {}

        # Check if running in backtest context
        backtest_dir = self.context.get("backtest_dir")

        if backtest_dir:
            # Use sandboxed backtest directory
            self.portfolios_dir = Path(portfolios_dir or Path(backtest_dir) / "portfolios")
            self.orders_dir = Path(orders_dir or Path(backtest_dir) / "orders")
        else:
            # Use normal directory
            db_root = get_db_root()
            self.portfolios_dir = Path(portfolios_dir or db_root / "portfolios")
            self.orders_dir = Path(orders_dir or db_root / "orders")

        config_root = get_config_root()
        self.config_path = Path(config_path or config_root / "portfolios.yml")
        self.portfolios_dir.mkdir(parents=True, exist_ok=True)
        self.orders_dir.mkdir(parents=True, exist_ok=True)
        self.cache = PortfolioCache(context=self.context)

    def list_portfolios(self) -> List[Dict[str, Any]]:
        """List all portfolios by scanning folders in portfolios directory."""
        portfolios = []

        # Ensure portfolios directory exists
        self.portfolios_dir.mkdir(parents=True, exist_ok=True)

        # Scan all folders in portfolios directory
        for portfolio_folder in self.portfolios_dir.iterdir():
            if not portfolio_folder.is_dir():
                continue

            portfolio_name = portfolio_folder.name
            portfolio_json = portfolio_folder / "portfolio.json"

            # Load portfolio metadata from portfolio.json
            if portfolio_json.exists():
                try:
                    with open(portfolio_json, 'r') as f:
                        metadata = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load portfolio.json for {portfolio_name}: {e}")
                    metadata = {
                        "name": portfolio_name,
                        "type": "paper",
                        "currency": "EUR",
                        "description": "",
                        "initial_capital": 100000.0,
                    }
            else:
                # Default metadata if portfolio.json doesn't exist
                metadata = {
                    "name": portfolio_name,
                    "type": "paper",
                    "currency": "EUR",
                    "description": "",
                    "initial_capital": 100000.0,
                }

            # Get journal stats
            journal = Journal(portfolio_name, context=self.context)
            df = journal.load_df()
            open_pos = journal.get_open_positions()
            completed = df[df["status"] == "completed"] if not df.empty else pd.DataFrame()

            # Calculate gains from metadata
            total_portfolio_value = metadata.get("total_portfolio_value", 0.0)
            initial_capital = metadata.get("initial_capital", 100000.0)
            unrealized_gain = total_portfolio_value - initial_capital
            unrealized_gain_pct = (unrealized_gain / initial_capital * 100) if initial_capital > 0 else 0.0

            portfolios.append({
                "name": metadata.get("name", portfolio_name),
                "type": metadata.get("type", "paper"),
                "currency": metadata.get("currency", "EUR"),
                "description": metadata.get("description", ""),
                "initial_capital": initial_capital,
                "total_portfolio_value": total_portfolio_value,
                "total_positions_value": metadata.get("total_positions_value", 0.0),
                "cash": metadata.get("cash", 0.0),
                "unrealized_gain": unrealized_gain,
                "unrealized_gain_pct": unrealized_gain_pct,
                "num_positions": len(open_pos),
                "num_trades": len(completed),
                "total_return_pct": metadata.get("total_return_pct", 0.0),
                "total_gain": metadata.get("total_gain", 0.0),
            })

        return portfolios

    def create_portfolio(
        self,
        name: str,
        portfolio_type: str = "paper",
        currency: str = "EUR",
        description: str = "",
        initial_capital: float = 100000.0,
    ) -> Dict[str, Any]:
        """Create a new portfolio folder with portfolio.json metadata."""
        try:
            # Create portfolio folder
            portfolio_dir = self.portfolios_dir / name
            portfolio_dir.mkdir(parents=True, exist_ok=True)

            # Check if portfolio already exists
            portfolio_json = portfolio_dir / "portfolio.json"
            if portfolio_json.exists():
                return {"status": "error", "message": f"Portfolio '{name}' already exists"}

            # Create portfolio.json with metadata
            portfolio_metadata = {
                "name": name,
                "type": portfolio_type,
                "currency": currency,
                "description": description,
                "initial_capital": initial_capital,
                "created_at": pd.Timestamp.now().isoformat(),
                "total_return_pct": 0.0,
                "total_gain": 0.0,
            }

            with open(portfolio_json, 'w') as f:
                json.dump(portfolio_metadata, f, indent=2)

            # Create journal file
            journal = Journal(name, context=self.context)
            if not journal.filepath.exists():
                journal._ensure_base_structure()

            logger.info(f"Created portfolio '{name}' with metadata in {portfolio_json}")

            # Update cache for new portfolio
            self.update_portfolio_cache(name)

            return {
                "status": "success",
                "portfolio": {
                    "name": name,
                    "type": portfolio_type,
                    "currency": currency,
                    "description": description,
                    "initial_capital": initial_capital,
                    "num_positions": 0,
                    "num_trades": 0,
                    "num_closed": 0,
                },
            }

        except Exception as e:
            logger.error(f"Error creating portfolio: {e}")
            return {"status": "error", "message": str(e)}

    def _get_portfolio_metadata(self, name: str) -> Dict[str, Any]:
        """Load portfolio metadata from portfolio.json file."""
        portfolio_json = self.portfolios_dir / name / "portfolio.json"

        if portfolio_json.exists():
            try:
                with open(portfolio_json, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load portfolio.json for {name}: {e}")

        # Return default metadata if file doesn't exist
        return {
            "name": name,
            "type": "paper",
            "currency": "EUR",
            "description": "",
            "initial_capital": 100000.0,
        }

    def _save_portfolio_metadata(self, name: str, metadata: Dict[str, Any]) -> None:
        """Save portfolio metadata to portfolio.json file."""
        portfolio_json = self.portfolios_dir / name / "portfolio.json"
        portfolio_json.parent.mkdir(parents=True, exist_ok=True)

        with open(portfolio_json, 'w') as f:
            json.dump(metadata, f, indent=2)

    def update_portfolio(self, name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update portfolio configuration."""
        try:
            # Load current metadata
            metadata = self._get_portfolio_metadata(name)

            # Update only provided fields
            allowed_fields = {"portfolio_type", "currency", "description", "initial_capital", "strategy"}
            field_mapping = {
                "portfolio_type": "type",  # Map API field to metadata field
                "currency": "currency",
                "description": "description",
                "initial_capital": "initial_capital",
                "strategy": "strategy",
            }

            for api_field, value in updates.items():
                if api_field in allowed_fields and value is not None:
                    metadata_field = field_mapping[api_field]
                    metadata[metadata_field] = value

            # Save updated metadata
            self._save_portfolio_metadata(name, metadata)

            logger.info(f"Updated portfolio '{name}' with: {updates}")

            return {
                "status": "success",
                "message": f"Portfolio '{name}' updated",
                "portfolio": metadata,
            }

        except Exception as e:
            logger.error(f"Error updating portfolio: {e}")
            return {"status": "error", "message": str(e)}

    def delete_portfolio(self, name: str) -> Dict[str, Any]:
        """Delete a portfolio folder and its contents."""
        try:
            # Delete portfolio folder
            portfolio_dir = self.portfolios_dir / name
            if portfolio_dir.exists():
                import shutil
                shutil.rmtree(portfolio_dir)
                logger.info(f"Deleted portfolio folder: {portfolio_dir}")

            # Delete journal file (if outside portfolio folder)
            journal = Journal(name, context=self.context)
            if journal.filepath.exists():
                journal.filepath.unlink()

            # Remove from cache
            self.cache.delete_portfolio(name)

            logger.info(f"Deleted portfolio '{name}'")

            return {"status": "success", "message": f"Portfolio '{name}' deleted"}

        except Exception as e:
            logger.error(f"Error deleting portfolio: {e}")
            return {"status": "error", "message": str(e)}

    def get_portfolio_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """Get portfolio metadata only (no expensive price lookups)."""
        metadata = self._get_portfolio_metadata(name)
        if not metadata:
            return None

        return {
            "name": name,
            "portfolio_type": metadata.get("type", "paper"),
            "currency": metadata.get("currency", "EUR"),
            "description": metadata.get("description", ""),
            "initial_capital": metadata.get("initial_capital", 100000.0),
            "created_at": metadata.get("created_at"),
            "strategy": metadata.get("strategy", name),
        }

    def get_portfolio_details(self, name: str) -> Optional[Dict[str, Any]]:
        """Get portfolio with positions and metadata."""
        # Load metadata
        metadata = self._get_portfolio_metadata(name)

        journal = Journal(name, context=self.context)
        df = journal.load_df()

        positions = []
        if not df.empty:
            open_pos = journal.get_open_positions()
            for _, row in open_pos.iterrows():
                ticker = row["ticker"]
                avg_entry_price = float(row["avg_entry_price"])
                quantity = float(row["quantity"])
                # Use cached current_price from portfolio.json instead of doing fresh lookup
                current_price = float(row.get("current_price", avg_entry_price))
                pos_value = quantity * current_price
                positions.append({
                    "ticker": ticker,
                    "quantity": quantity,
                    "avg_entry_price": avg_entry_price,
                    "current_price": current_price,
                    "position_value": round(pos_value, 2),
                    "position_gain": round((current_price - avg_entry_price) * quantity, 2),
                    "position_gain_pct": round(((current_price - avg_entry_price) / avg_entry_price * 100), 2) if avg_entry_price > 0 else 0,
                })

        completed = df[df["status"] == "completed"] if not df.empty else pd.DataFrame()
        return {
            "name": name,
            "portfolio_type": metadata.get("type", "paper"),
            "currency": metadata.get("currency", "EUR"),
            "description": metadata.get("description", ""),
            "initial_capital": metadata.get("initial_capital", 100000.0),
            "created_at": metadata.get("created_at"),
            "strategy": metadata.get("strategy", name),  # Default to portfolio name if not set
            "num_positions": len(positions),
            "num_trades": len(completed),
            "positions": positions,
            "total_value": sum(p["position_value"] for p in positions) if positions else 0,
        }

    def get_portfolio_positions(self, name: str) -> Optional[Dict[str, Any]]:
        """Get open positions."""
        journal = Journal(name, context=self.context)
        open_pos = journal.get_open_positions()
        positions = []
        for _, row in open_pos.iterrows():
            ticker = row["ticker"]
            quantity = float(row["quantity"])
            avg_entry_price = float(row["avg_entry_price"])
            current_price = Fundamental(ticker).get_current_price() or avg_entry_price
            positions.append({
                "ticker": ticker,
                "quantity": quantity,
                "avg_entry_price": avg_entry_price,
                "current_price": current_price,
                "position_value": round(quantity * current_price, 2),
            })
        return {"positions": positions, "total_value": sum(p["position_value"] for p in positions)}

    def get_portfolio_performance(self, name: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics."""
        journal = Journal(name, context=self.context)
        df = journal.load_df()

        if df.empty:
            return {
                "num_trades": 0,
                "buy_trades": 0,
                "sell_trades": 0,
                "total_fees": 0.0,
                "total_gain_pct": 0.0,
            }

        completed_df = df[df["status"] == "completed"]
        total_fees = sum(pd.to_numeric(completed_df["fees"], errors='coerce').fillna(0)) if len(completed_df) > 0 else 0.0

        buy_count = len(df[df["operation"].str.upper() == "BUY"])
        sell_count = len(df[df["operation"].str.upper() == "SELL"])

        return {
            "num_trades": len(completed_df),
            "buy_trades": buy_count,
            "sell_trades": sell_count,
            "total_fees": round(total_fees, 2),
            "total_gain_pct": 0.0,
        }

    def get_portfolio_cash(self, name: str) -> float:
        """Calculate available cash balance."""
        # Get initial capital from portfolio metadata
        metadata = self._get_portfolio_metadata(name)
        initial_capital = float(metadata.get("initial_capital", 100000.0))

        # Calculate cash from transactions
        journal = Journal(name, context=self.context)
        df = journal.load_df()

        if df.empty:
            return initial_capital

        cash = initial_capital
        for _, row in df.iterrows():
            operation = str(row["operation"]).upper()
            quantity = float(row["quantity"])
            price = float(row["price"])
            fees = float(row.get("fees", 0))

            if operation == "BUY":
                cash -= (quantity * price + fees)
            elif operation == "SELL":
                cash += (quantity * price - fees)
            elif operation == "CASH":
                # For CASH: quantity is the amount (positive=deposit, negative=withdrawal)
                cash += quantity

        return round(cash, 2)

    def update_portfolio_cache(self, name: str) -> None:
        """Update portfolio cache and portfolio.json metadata with latest metrics (minimal cache - no position data)."""
        details = self.get_portfolio_details(name)
        perf = self.get_portfolio_performance(name)
        cash = self.get_portfolio_cash(name)

        if not details or not perf:
            return

        # Get current portfolio metadata
        metadata = self._get_portfolio_metadata(name)

        # Build minimal cache entry (summary only, NO position data)
        total_value = details.get("total_value", 0)
        total_portfolio_value = total_value + cash
        num_positions = details.get("num_positions", 0)

        cache_entry = {
            "name": name,
            "type": metadata.get("type", "paper"),
            "currency": metadata.get("currency", "EUR"),
            "description": metadata.get("description", ""),
            "initial_capital": float(metadata.get("initial_capital", 100000.0)),
            "total_portfolio_value": round(total_portfolio_value, 2),
            "total_positions_value": round(total_value, 2),
            "cash": round(cash, 2),
            "num_positions": num_positions,
            "num_trades": perf.get("num_trades", 0),
        }

        # Update portfolio.json metadata with latest metrics
        metadata.update({
            "total_positions_value": round(total_value, 2),
            "cash": round(cash, 2),
            "total_portfolio_value": round(total_portfolio_value, 2),
            "num_positions": num_positions,
            "num_trades": perf.get("num_trades", 0),
            "updated_at": pd.Timestamp.now().isoformat(),
        })
        self._save_portfolio_metadata(name, metadata)

        # Update cache
        self.cache.update_portfolio(name, cache_entry)

    def get_portfolio_summary(self, name: str) -> Optional[Dict[str, Any]]:
        """Get portfolio summary."""
        details = self.get_portfolio_details(name)
        perf = self.get_portfolio_performance(name)
        if not details or not perf:
            return None
        return {**details, **perf}

    def calculate_portfolio_value(self, name: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get current portfolio value."""
        positions = self.get_portfolio_positions(name)
        if not positions:
            return {"error": f"Portfolio '{name}' not found"}
        return {
            "portfolio_name": name,
            "total_value": positions.get("total_value", 0),
            "positions": positions.get("positions", []),
        }

    def calculate_portfolio_history(self, name: str, recalculate: bool = False, use_cache_only: bool = False) -> Dict[str, Any]:
        """Get portfolio value history from transactions.

        Replays journal transactions to compute daily portfolio value including cash.

        Args:
            name: Portfolio name
            recalculate: If True, recalculate even if cached
            use_cache_only: If True, only use cached data (skip fetching for API endpoints)
        """
        # Get initial capital from portfolio metadata
        metadata = self._get_portfolio_metadata(name)
        initial_capital = float(metadata.get("initial_capital", 100000.0))

        # Use PortfolioHistory to calculate
        ph = PortfolioHistory(name, initial_capital)
        result = ph.calculate(recalculate, use_cache_only=use_cache_only)

        if result.get("status") == "error":
            return {
                "portfolio_name": name,
                "history": [
                    {"date": "2026-01-01", "value": initial_capital},
                    {"date": "2026-05-01", "value": initial_capital},
                ],
            }

        return result


    def record_transaction(self, portfolio_name: str, operation: str, ticker: str, quantity: int, price: float, fees: float = 0, notes: str = "", created_at: Optional[str] = None) -> Dict[str, Any]:
        """Record a transaction (BUY, SELL, or CASH).

        CASH operations: ticker should be "CASH", quantity is the amount (positive=deposit, negative=withdrawal)
        After recording, automatically fetches history and fundamental data for the ticker.
        """
        journal = Journal(portfolio_name, context=self.context)
        operation_upper = operation.upper()

        if operation_upper not in ("BUY", "SELL", "CASH"):
            return {"status": "error", "message": f"Unknown operation: {operation}"}

        try:
            tx_id = journal.add_transaction(
                operation=operation_upper,
                ticker=ticker,
                quantity=quantity,
                price=price,
                fees=fees,
                notes=notes,
                created_at=created_at
            )
            # Flush to disk immediately (don't wait for context flush)
            journal.flush()

            # Fetch history and fundamental data for the ticker (unless it's CASH)
            if operation_upper != "CASH" and ticker.upper() != "CASH":
                try:
                    logger.info(f"Fetching data for {ticker}")
                    # Fetch history data
                    dh = DataHistory(ticker)
                    dh.fetch()
                    # Fetch fundamental data
                    fund = Fundamental(ticker)
                    fund.fetch()
                except Exception as fetch_error:
                    logger.warning(f"Failed to fetch data for {ticker}: {fetch_error}")
                    # Don't fail the transaction if data fetch fails
                    pass

            # Update cache after successful transaction
            self.update_portfolio_cache(portfolio_name)
            return {
                "status": "success",
                "operation": "buy" if operation_upper == "BUY" else "sell",
                "transaction_id": tx_id
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_portfolio_transactions(self, portfolio_name: str, ticker: Optional[str] = None) -> Dict[str, Any]:
        """Get transactions for a portfolio, optionally filtered by ticker."""
        journal = Journal(portfolio_name, context=self.context)
        df = journal.load_df()

        if df.empty:
            return {"transactions": []}

        # Filter by ticker if specified
        if ticker:
            df = df[df["ticker"].str.upper() == ticker.upper()]

        # Convert to list of dicts
        transactions = []
        for _, row in df.iterrows():
            quantity = float(row.get("quantity", 0))
            price = float(row.get("price", 0))
            amount = float(row.get("amount", 0))
            # Calculate amount if not present
            if amount == 0 and quantity > 0 and price > 0:
                amount = quantity * price

            tx = {
                "id": str(row.get("id", "")),
                "created_at": str(row.get("created_at", "")),
                "operation": str(row.get("operation", "")),
                "ticker": str(row.get("ticker", "")),
                "quantity": quantity,
                "price": price,
                "amount": amount,
                "fees": float(row.get("fees", 0)),
                "status": str(row.get("status", "")),
                "status_at": str(row.get("status_at", "")),
                "notes": str(row.get("notes", "")),
            }
            transactions.append(tx)

        return {"transactions": transactions}

    def update_transaction(self, portfolio_name: str, transaction_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a transaction."""
        journal = Journal(portfolio_name, context=self.context)
        try:
            journal.update_transaction(transaction_id, updates)
            journal.flush()
            self.update_portfolio_cache(portfolio_name)
            return {"status": "success", "message": "Transaction updated"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_transaction(self, portfolio_name: str, transaction_id: str) -> Dict[str, Any]:
        """Delete a transaction."""
        journal = Journal(portfolio_name, context=self.context)
        try:
            journal.delete_transaction(transaction_id)
            journal.flush()
            self.update_portfolio_cache(portfolio_name)
            return {"status": "success", "message": "Transaction deleted"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_portfolio_orders(self, portfolio_name: str) -> Dict[str, Any]:
        """Get pending and executed orders for a portfolio."""
        from tools.portfolio.orders import Orders

        try:
            orders_mgr = Orders(portfolio_name)
            all_orders = orders_mgr.to_orders()

            if not all_orders:
                return {"orders": [], "count": 0}

            # Convert to API format
            orders = []
            for order in all_orders:
                api_order = {
                    "id": order["id"][:8],
                    "ticker": order["ticker"],
                    "shares": order["quantity"],
                    "entryPrice": order["entry_price"],
                    "executionMethod": order["execution_method"],
                    "stopLoss": order["stop_loss"],
                    "takeProfit": order["take_profit"],
                    "riskAmount": order["risk_amount"],
                    "riskReward": order["risk_reward"],
                    "status": order["status"].upper(),
                    "createdAt": order["created_at"],
                    "metadata": order["metadata"],
                }
                orders.append(api_order)

            # Sort by date descending
            orders.sort(key=lambda x: x["createdAt"], reverse=True)
            return {"orders": orders, "count": len(orders)}
        except Exception as e:
            logger.error(f"Error fetching orders for {portfolio_name}: {e}")
            return {"orders": [], "count": 0}

    def refresh_portfolio_fundamentals(self, name: str) -> Dict[str, Any]:
        """Refresh prices for all positions."""
        positions = self.get_portfolio_positions(name)
        if not positions:
            return {"error": f"Portfolio '{name}' not found"}

        refreshed = 0
        for pos in positions.get("positions", []):
            Fundamental(pos["ticker"]).fetch()
            refreshed += 1

        return {"status": "success", "refreshed": refreshed}

    def get_portfolio_allocation(self, name: str) -> Optional[Dict[str, Any]]:
        """Get portfolio allocation by position weight."""
        details = self.get_portfolio_details(name)

        total_value = details.get("total_value", 0)
        if total_value <= 0:
            return {"total_value": 0.0, "positions": []}

        positions_by_weight = []
        for pos in details.get("positions", []):
            weight = (pos["position_value"] / total_value * 100) if total_value > 0 else 0
            positions_by_weight.append({
                "ticker": pos["ticker"],
                "weight": round(weight, 2),
                "value": round(pos["position_value"], 2),
                "quantity": pos["quantity"],
            })

        # Sort by weight descending
        positions_by_weight.sort(key=lambda x: x["weight"], reverse=True)

        return {
            "total_value": round(total_value, 2),
            "positions": positions_by_weight,
        }

    def get_top_holdings(self, name: str, limit: int = 10) -> Optional[Dict[str, Any]]:
        """Get top holdings by weight."""
        details = self.get_portfolio_details(name)
        perf = self.get_portfolio_performance(name)

        from tools.data import DataHistory
        from datetime import datetime

        total_value = details.get("total_value", 0)
        top_holdings = []

        if not details.get("positions"):
            return {"holdings": [], "total_value": 0.0}

        for pos in details.get("positions", []):
            ticker = pos["ticker"]
            weight = (pos["position_value"] / total_value * 100) if total_value > 0 else 0

            # Get historical data for today and YTD change
            data_hist = DataHistory(ticker)
            df = data_hist.get_all()

            today_change = 0
            ytd_change = 0

            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
                latest = df.sort_values("timestamp").iloc[-1]
                previous = df[df["timestamp"] < latest["timestamp"]]
                if not previous.empty:
                    prev_close = previous.sort_values("timestamp").iloc[-1]["close"]
                    today_change = ((latest["close"] - prev_close) / prev_close * 100)

                # YTD change (from Jan 1 of current year)
                ytd_start = datetime(datetime.now().year, 1, 1)
                ytd_start_ts = pd.Timestamp(ytd_start)
                df_ytd = df[df["timestamp"] >= ytd_start_ts]
                if not df_ytd.empty:
                    ytd_close = df_ytd.sort_values("timestamp").iloc[-1]["close"]
                    ytd_open = df_ytd.sort_values("timestamp").iloc[0]["open"]
                    ytd_change = ((ytd_close - ytd_open) / ytd_open * 100)

            top_holdings.append({
                "ticker": ticker,
                "name": ticker,
                "weight": round(weight, 2),
                "value": round(pos["position_value"], 2),
                "quantity": pos["quantity"],
                "today_change": round(today_change, 2),
                "ytd_change": round(ytd_change, 2),
            })

        # Sort by weight and limit
        top_holdings.sort(key=lambda x: x["weight"], reverse=True)
        return {
            "holdings": top_holdings[:limit],
            "total_value": round(total_value, 2),
        }

    def get_all_portfolio_tickers(self) -> List[str]:
        """Get all unique tickers from all real portfolios (journals and watchlist).

        Returns:
            List of unique ticker symbols
        """
        tickers = set()

        # Get all real portfolios
        portfolios = self.list_portfolios()
        real_portfolios = [p for p in portfolios if p["type"] == "real"]

        logger.info(f"Scanning {len(real_portfolios)} real portfolios for tickers")

        # Get tickers from journal (transactions)
        for portfolio in real_portfolios:
            portfolio_name = portfolio["name"]
            try:
                journal = Journal(portfolio_name, context=self.context)
                df = journal.load_df()

                if not df.empty:
                    # Get unique tickers from journal (skip CASH operations)
                    journal_tickers = df[df["ticker"] != "CASH"]["ticker"].unique().tolist()
                    tickers.update(journal_tickers)
                    logger.debug(f"  {portfolio_name}: {len(journal_tickers)} tickers from journal")
            except Exception as e:
                logger.warning(f"Error reading journal for {portfolio_name}: {e}")

        # Get tickers from watchlist (if available)
        # Note: WatchlistManager is strategy-specific, so skip for now
        # Watchlist tickers are less critical since they're strategy-dependent
        logger.debug("Skipping watchlist (strategy-specific data)")

        ticker_list = sorted(list(tickers))
        logger.info(f"Total unique tickers across all real portfolios: {len(ticker_list)}")
        logger.debug(f"Tickers: {ticker_list}")

        return ticker_list

    def fetch_all_ticker_data(self, days: int = 365) -> Dict[str, Any]:
        """Fetch history and fundamental data for all portfolio tickers.

        This pre-caches data to avoid slow API calls during portfolio operations.

        Args:
            days: Number of days of history to fetch (default: 365)

        Returns:
            Dictionary with fetch results
        """
        tickers = self.get_all_portfolio_tickers()

        if not tickers:
            logger.info("No tickers to fetch")
            return {
                "status": "success",
                "tickers_processed": 0,
                "tickers_failed": [],
            }

        logger.info(f"Fetching data for {len(tickers)} tickers (last {days} days)")

        failed_tickers = []
        success_count = 0

        for ticker in tickers:
            try:
                # Fetch history data (loads from cache or yfinance)
                history = DataHistory(ticker)
                hist_result = history.fetch()

                # Fetch fundamental data
                fundamental = Fundamental(ticker)
                fund_result = fundamental.fetch()

                if hist_result.get("status") == "success" and fund_result.get("status") == "success":
                    success_count += 1
                    price = fund_result.get("current_price", 0)
                    logger.debug(f"  ✓ {ticker}: history loaded, price €{price:.2f}")
                else:
                    failed_tickers.append(ticker)
                    logger.warning(f"  ✗ {ticker}: incomplete data")

            except Exception as e:
                failed_tickers.append(ticker)
                logger.warning(f"  ✗ {ticker}: {str(e)[:100]}")

        result = {
            "status": "success" if not failed_tickers else "partial",
            "tickers_processed": success_count,
            "tickers_failed": failed_tickers,
            "tickers_total": len(tickers),
        }

        logger.info(f"Fetch complete: {success_count}/{len(tickers)} successful")

        return result

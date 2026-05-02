"""Broker abstraction for order execution.

Supports paper trading (default) and real brokers (Interactive Brokers, etc).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class ExecutionResult:
    """Result of order execution."""
    order_id: str
    status: str  # "filled", "partial", "rejected", "pending"
    filled_price: Optional[float] = None
    filled_quantity: Optional[int] = None
    executed_at: Optional[str] = None
    reason: Optional[str] = None


class Broker(ABC):
    """Abstract broker interface."""

    @abstractmethod
    def execute_order(self, order: Dict[str, Any]) -> ExecutionResult:
        """Execute a buy/sell order.

        Args:
            order: Order dict with ticker, quantity, action (BUY/SELL), price

        Returns:
            ExecutionResult with status and filled details
        """
        pass

    @abstractmethod
    def get_position(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get current position for ticker.

        Returns:
            Position dict with quantity, entry_price, current_price, pnl
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel pending order."""
        pass

    @abstractmethod
    def get_account_balance(self) -> float:
        """Get available cash balance."""
        pass


class PaperBroker(Broker):
    """Paper trading broker - simulates execution without real money.

    Used for backtesting and paper trading. Can be swapped for IBroker
    or other real brokers without changing TraderAgent code.
    """

    def __init__(self, initial_balance: float = 100000.0):
        """Initialize paper broker.

        Args:
            initial_balance: Starting cash balance for paper trading
        """
        self.balance = initial_balance
        self.positions: Dict[str, Dict[str, Any]] = {}  # ticker -> position
        self.orders: Dict[str, Dict[str, Any]] = {}     # order_id -> order
        self.fills: List[Dict[str, Any]] = []           # Execution history

    def execute_order(self, order: Dict[str, Any]) -> ExecutionResult:
        """Execute order immediately (paper trading).

        Args:
            order: {
                "ticker": "AAPL",
                "quantity": 100,
                "action": "BUY" | "SELL",
                "price": 150.50,  # current price
                "stop_loss": 145.00,
                "target_price": 160.00,
                "strategy_id": "ta_cac_1"
            }

        Returns:
            ExecutionResult with filled details
        """
        ticker = order.get("ticker")
        quantity = order.get("quantity", 0)
        action = order.get("action", "BUY")
        price = order.get("price", 0)

        if not ticker or not quantity or not price:
            return ExecutionResult(
                order_id=str(uuid.uuid4()),
                status="rejected",
                reason="Missing required fields: ticker, quantity, price"
            )

        # Check balance for BUY orders
        cost = quantity * price
        if action == "BUY" and cost > self.balance:
            return ExecutionResult(
                order_id=str(uuid.uuid4()),
                status="rejected",
                reason=f"Insufficient balance: need {cost}, have {self.balance}"
            )

        order_id = str(uuid.uuid4())

        # Execute order
        if action == "BUY":
            self.balance -= cost

            if ticker in self.positions:
                pos = self.positions[ticker]
                pos["quantity"] += quantity
                pos["entry_price"] = (pos["entry_price"] * (pos["quantity"] - quantity) + price * quantity) / pos["quantity"]
            else:
                self.positions[ticker] = {
                    "ticker": ticker,
                    "quantity": quantity,
                    "entry_price": price,
                    "current_price": price,
                    "stop_loss": order.get("stop_loss"),
                    "target_price": order.get("target_price"),
                    "strategy_id": order.get("strategy_id"),
                }

        elif action == "SELL":
            if ticker not in self.positions or self.positions[ticker]["quantity"] < quantity:
                return ExecutionResult(
                    order_id=order_id,
                    status="rejected",
                    reason=f"Insufficient position: need {quantity}, have {self.positions.get(ticker, {}).get('quantity', 0)}"
                )

            pos = self.positions[ticker]
            self.balance += quantity * price
            pos["quantity"] -= quantity

            if pos["quantity"] == 0:
                del self.positions[ticker]

        # Record execution
        execution = ExecutionResult(
            order_id=order_id,
            status="filled",
            filled_price=price,
            filled_quantity=quantity,
            executed_at=datetime.now().isoformat()
        )

        self.fills.append({
            "order_id": order_id,
            "ticker": ticker,
            "action": action,
            "quantity": quantity,
            "price": price,
            "strategy_id": order.get("strategy_id"),
            "executed_at": execution.executed_at,
        })

        return execution

    def get_position(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get current position."""
        if ticker in self.positions:
            pos = self.positions[ticker].copy()
            # Update current price and PnL would come from real-time data
            pos["pnl"] = (pos["current_price"] - pos["entry_price"]) * pos["quantity"]
            return pos
        return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order (paper trading doesn't have pending orders)."""
        return False  # All orders fill immediately in paper trading

    def get_account_balance(self) -> float:
        """Get available cash."""
        return self.balance

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get all positions."""
        return self.positions.copy()

    def get_equity(self) -> float:
        """Get total portfolio value (cash + positions)."""
        equity = self.balance
        # Would need current prices from real-time data
        return equity


class IBrokerAdapter(Broker):
    """Interactive Brokers adapter (placeholder for real implementation).

    Swap this in for PaperBroker to trade with real money.
    """

    def __init__(self, account_id: str, api_key: str):
        self.account_id = account_id
        self.api_key = api_key
        # Would connect to IB Gateway/TWS here

    def execute_order(self, order: Dict[str, Any]) -> ExecutionResult:
        """Execute real order via IB."""
        # TODO: Implement IB API calls
        raise NotImplementedError("IBroker integration pending")

    def get_position(self, ticker: str) -> Optional[Dict[str, Any]]:
        # TODO: Query IB for position
        raise NotImplementedError("IBroker integration pending")

    def cancel_order(self, order_id: str) -> bool:
        # TODO: Cancel IB order
        raise NotImplementedError("IBroker integration pending")

    def get_account_balance(self) -> float:
        # TODO: Get IB account balance
        raise NotImplementedError("IBroker integration pending")

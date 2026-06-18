"""
Portfolio engine for backtesting with proper position tracking and P&L calculation.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class Position:
    """Tracks a single buy/sell pair for a ticker."""

    def __init__(self, ticker: str, entry_date: datetime, entry_price: float, quantity: int, fees: float):
        self.ticker = ticker
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.quantity = quantity
        self.fees = fees
        self.entry_cost = entry_price * quantity + fees
        self.exit_date: Optional[datetime] = None
        self.exit_price: Optional[float] = None
        self.exit_quantity: Optional[int] = None
        self.exit_fees: Optional[float] = None
        self.closed = False

    def close(self, exit_date: datetime, exit_price: float, exit_quantity: int, exit_fees: float) -> float:
        """Close position and return realized P&L."""
        assert exit_quantity <= self.quantity, f"Cannot sell {exit_quantity} of {self.quantity} shares"

        self.exit_date = exit_date
        self.exit_price = exit_price
        self.exit_quantity = exit_quantity
        self.exit_fees = exit_fees

        exit_proceeds = exit_price * exit_quantity - exit_fees
        entry_cost_partial = (self.entry_cost / self.quantity) * exit_quantity

        pnl = exit_proceeds - entry_cost_partial
        pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100

        self.quantity -= exit_quantity
        self.closed = self.quantity == 0

        return pnl, pnl_pct

    def __repr__(self):
        status = "CLOSED" if self.closed else f"OPEN ({self.quantity} shares)"
        return f"Position({self.ticker} @ €{self.entry_price:.2f}, {status})"


class PortfolioEngine:
    """Backtesting portfolio with proper position tracking."""

    def __init__(self, initial_capital: float = 10000.0, fee_rate: float = 0.001):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.fee_rate = fee_rate  # 0.1% (10 basis points)

        self.positions: List[Position] = []  # Open positions
        self.closed_positions: List[Position] = []  # Closed positions
        self.trades: List[Dict] = []
        self.cash_history: List[Tuple[datetime, float]] = []
        self.pnl_trades: List[float] = []

    def add_cash(self, date: datetime, amount: float, notes: str = ""):
        """Add or withdraw cash."""
        self.cash += amount
        self.cash_history.append((date, self.cash))
        self.trades.append({
            'Date': date,
            'Type': 'CASH',
            'Ticker': 'CASH',
            'Quantity': amount,
            'Price': 1.0,
            'Fees': 0.0,
            'Cash': self.cash,
            'Notes': notes
        })

    def buy(self, date: datetime, ticker: str, price: float, quantity: int) -> bool:
        """Buy shares. Returns False if insufficient cash."""
        fees = price * quantity * self.fee_rate
        cost = price * quantity + fees

        if cost > self.cash:
            return False  # Insufficient cash

        self.cash -= cost
        pos = Position(ticker, date, price, quantity, fees)
        self.positions.append(pos)

        self.trades.append({
            'Date': date,
            'Type': 'BUY',
            'Ticker': ticker,
            'Quantity': quantity,
            'Price': price,
            'Fees': fees,
            'Cash': self.cash,
        })

        return True

    def sell(self, date: datetime, ticker: str, price: float, quantity: int) -> Tuple[bool, List[float]]:
        """
        Sell shares using FIFO matching.
        Returns (success, list of P&L % for matched positions)
        """
        # Get open positions for this ticker (FIFO order)
        ticker_positions = [p for p in self.positions if p.ticker == ticker and not p.closed]

        if not ticker_positions:
            return False, []  # No positions to sell

        # Calculate total available shares
        total_available = sum(p.quantity for p in ticker_positions)
        if quantity > total_available:
            return False, []  # Can't sell more than we own

        fees = price * quantity * self.fee_rate
        proceeds = price * quantity - fees
        self.cash += proceeds

        pnl_list = []
        qty_to_sell = quantity

        # FIFO: match against oldest positions first
        for pos in ticker_positions:
            if qty_to_sell == 0:
                break

            sell_qty = min(qty_to_sell, pos.quantity)
            pnl, pnl_pct = pos.close(date, price, sell_qty, (fees * sell_qty / quantity))

            pnl_list.append(pnl_pct)
            self.pnl_trades.append(pnl_pct)
            qty_to_sell -= sell_qty

            if pos.closed:
                self.closed_positions.append(pos)
                self.positions.remove(pos)

        self.trades.append({
            'Date': date,
            'Type': 'SELL',
            'Ticker': ticker,
            'Quantity': quantity,
            'Price': price,
            'Fees': fees,
            'Cash': self.cash,
        })

        return True, pnl_list

    def rebalance(self, date: datetime, trades_df: pd.DataFrame):
        """
        Execute all trades from a rebalancing period using weight-based allocation.
        Trades should be sorted by date and grouped by date.
        """
        day_trades = trades_df[trades_df['Date'] == date].copy()

        # First: execute ALL SELLS for this date (sell first, then buy)
        for _, trade in day_trades[day_trades['Type'] == 'SELL'].iterrows():
            ticker = trade['Ticker']
            price = float(trade['Price'].replace('€', '').strip())
            quantity = int(trade['Quantity'])

            if price <= 0:
                continue

            # Get current open quantity for this ticker
            ticker_positions = [p for p in self.positions if p.ticker == ticker and not p.closed]
            available_qty = sum(p.quantity for p in ticker_positions)

            if available_qty > 0:
                # IMPORTANT: Sell ALL shares in this ticker (even if more/less than expected)
                # because this stock is exiting the top 5
                success, pnl_list = self.sell(date, ticker, price, available_qty)

        # Second: execute ALL BUYS for this date
        for _, trade in day_trades[day_trades['Type'] == 'BUY'].iterrows():
            ticker = trade['Ticker']
            price = float(trade['Price'].replace('€', '').strip())
            quantity = int(trade['Quantity'])

            if quantity <= 0 or price <= 0:
                continue

            self.buy(date, ticker, price, quantity)

    def get_metrics(self) -> Dict:
        """Calculate portfolio metrics."""
        if not self.pnl_trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'avg_win': 0,
                'avg_loss': 0,
            }

        wins = sum(1 for p in self.pnl_trades if p > 0)
        losses = sum(1 for p in self.pnl_trades if p <= 0)

        return {
            'total_trades': len(self.pnl_trades),
            'closed_trades': len(self.closed_positions),
            'open_positions': len(self.positions),
            'win_rate': (wins / len(self.pnl_trades) * 100) if self.pnl_trades else 0,
            'best_trade': max(self.pnl_trades) if self.pnl_trades else 0,
            'worst_trade': min(self.pnl_trades) if self.pnl_trades else 0,
            'avg_win': np.mean([p for p in self.pnl_trades if p > 0]) if wins > 0 else 0,
            'avg_loss': np.mean([p for p in self.pnl_trades if p <= 0]) if losses > 0 else 0,
            'total_fees': sum(t.get('Fees', 0) for t in self.trades),
            'cash': self.cash,
        }

    def portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate current portfolio value at given prices."""
        position_value = sum(pos.quantity * current_prices.get(pos.ticker, pos.entry_price)
                            for pos in self.positions)
        return self.cash + position_value


def run_portfolio_backtest(trades_df: pd.DataFrame, initial_capital: float = 10000.0) -> PortfolioEngine:
    """Run complete portfolio backtest from trades DataFrame."""

    portfolio = PortfolioEngine(initial_capital=initial_capital, fee_rate=0.005)
    portfolio.add_cash(trades_df['Date'].min(), initial_capital, "Initial capital")

    # Process trades by date
    for date in sorted(trades_df['Date'].unique()):
        portfolio.rebalance(date, trades_df)

    return portfolio

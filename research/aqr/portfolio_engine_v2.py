"""
Simplified portfolio engine for equal-weight momentum strategy.
Maintains exactly N positions at equal weights.
Includes QuantStats analytics integration.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional

try:
    import quantstats as qs
    HAS_QUANTSTATS = True
except ImportError:
    HAS_QUANTSTATS = False


class Position:
    """Track a single closed position."""
    def __init__(self, ticker: str, entry_date: datetime, entry_price: float, quantity: int):
        self.ticker = ticker
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.quantity = quantity
        self.exit_date = None
        self.exit_price = None
        self.pnl_pct = 0


class SimplePortfolio:
    """
    Portfolio tracking for equal-weight rebalancing strategy.
    Tracks current holdings and values.
    """

    def __init__(self, initial_capital: float = 10000.0, fee_rate: float = 0.0015):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.fee_rate = fee_rate  # 0.1% = 0.001

        self.holdings = {}  # {ticker: {'shares': int, 'avg_entry': float}}
        self.trades = []  # List of all trades
        self.pnl_history = []  # List of realized P&L
        self.closed_positions = []  # List of closed positions (for compatibility)
        self.daily_values = []  # Daily portfolio values for returns calculation
        self.daily_dates = []  # Dates for daily values

    def buy(self, date: datetime, ticker: str, price: float, quantity: int) -> bool:
        """Buy shares."""
        if quantity <= 0 or price <= 0:
            return False

        fees = price * quantity * self.fee_rate
        cost = price * quantity + fees

        if cost > self.cash:
            return False  # Insufficient cash

        self.cash -= cost

        if ticker not in self.holdings:
            self.holdings[ticker] = {'shares': 0, 'avg_entry': 0, 'entry_value': 0}

        # Track cost basis
        old_value = self.holdings[ticker]['avg_entry'] * self.holdings[ticker]['shares']
        self.holdings[ticker]['shares'] += quantity
        self.holdings[ticker]['entry_value'] += cost
        if self.holdings[ticker]['shares'] > 0:
            self.holdings[ticker]['avg_entry'] = self.holdings[ticker]['entry_value'] / self.holdings[ticker]['shares']

        self.trades.append({
            'Date': date,
            'Type': 'BUY',
            'Ticker': ticker,
            'Price': price,
            'Quantity': quantity,
            'Fees': fees,
            'Cash': self.cash,
        })

        return True

    def sell(self, date: datetime, ticker: str, price: float, quantity: int) -> Tuple[bool, float]:
        """Sell shares. Returns (success, realized_pnl)."""
        if ticker not in self.holdings:
            return False, 0.0

        available = self.holdings[ticker]['shares']
        if quantity > available:
            return False, 0.0

        fees = price * quantity * self.fee_rate
        proceeds = price * quantity - fees

        # Calculate P&L
        cost_basis = (self.holdings[ticker]['entry_value'] / available) * quantity
        pnl = proceeds - cost_basis
        pnl_pct = ((price - self.holdings[ticker]['avg_entry']) / self.holdings[ticker]['avg_entry']) * 100

        self.cash += proceeds
        self.holdings[ticker]['shares'] -= quantity
        self.holdings[ticker]['entry_value'] -= cost_basis

        # Track closed position
        pos = Position(ticker, date, self.holdings[ticker]['avg_entry'], quantity)
        pos.exit_date = date
        pos.exit_price = price
        pos.pnl_pct = pnl_pct
        self.closed_positions.append(pos)

        if self.holdings[ticker]['shares'] == 0:
            del self.holdings[ticker]

        self.trades.append({
            'Date': date,
            'Type': 'SELL',
            'Ticker': ticker,
            'Price': price,
            'Quantity': quantity,
            'Fees': fees,
            'Cash': self.cash,
        })

        self.pnl_history.append(pnl_pct)
        return True, pnl

    def get_value(self, current_prices: Dict[str, float]) -> float:
        """Get current portfolio value at given prices."""
        position_value = sum(self.holdings[ticker]['shares'] * current_prices.get(ticker, self.holdings[ticker]['avg_entry'])
                            for ticker in self.holdings)
        return self.cash + position_value

    def get_metrics(self) -> Dict:
        """Get portfolio metrics."""
        if not self.pnl_history:
            return {
                'trades': len(self.trades),
                'realized_pnl': 0,
                'win_rate': 0,
                'best': 0,
                'worst': 0,
            }

        wins = sum(1 for p in self.pnl_history if p > 0)
        return {
            'trades': len(self.trades),
            'realized_pnl': sum(self.pnl_history),
            'win_rate': (wins / len(self.pnl_history) * 100) if self.pnl_history else 0,
            'best': max(self.pnl_history),
            'worst': min(self.pnl_history),
            'avg_pnl': np.mean(self.pnl_history),
        }

    def analyze_with_quantstats(self, daily_returns: pd.Series, benchmark: pd.Series = None) -> Dict:
        """Generate QuantStats analytics report."""
        if not HAS_QUANTSTATS:
            return {'error': 'QuantStats not installed. Install with: pip install quantstats'}

        try:
            # QuantStats v0.59+ API uses cumulative returns
            cumulative_returns = (1 + daily_returns).cumprod()

            stats = {
                'total_return': cumulative_returns.iloc[-1] - 1,
                'annual_return': (cumulative_returns.iloc[-1] ** (252 / len(daily_returns)) - 1) if len(daily_returns) > 0 else 0,
                'sharpe': daily_returns.mean() * 252 / (daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0,
                'sortino': daily_returns.mean() * 252 / (daily_returns[daily_returns < 0].std() * np.sqrt(252)) if daily_returns[daily_returns < 0].std() > 0 else 0,
                'max_drawdown': (cumulative_returns / cumulative_returns.cummax() - 1).min(),
                'avg_drawdown': (cumulative_returns / cumulative_returns.cummax() - 1).mean(),
                'win_rate': (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0,
                'best_day': daily_returns.max(),
                'worst_day': daily_returns.min(),
                'volatility': daily_returns.std() * np.sqrt(252),
                'skew': daily_returns.skew(),
                'kurtosis': daily_returns.kurtosis(),
            }

            # Calmar ratio
            annual_ret = stats['annual_return']
            max_dd = abs(stats['max_drawdown'])
            stats['calmar'] = annual_ret / max_dd if max_dd > 0 else 0

            if benchmark is not None:
                # Beta, Alpha, Correlation
                covariance = np.cov(daily_returns, benchmark)[0, 1]
                variance = np.var(benchmark)
                stats['beta'] = covariance / variance if variance > 0 else 0
                stats['alpha'] = daily_returns.mean() - (benchmark.mean() + stats['beta'] * (benchmark.mean() - 0.001/252))
                stats['correlation'] = daily_returns.corr(benchmark)

            return stats
        except Exception as e:
            return {'error': f'QuantStats analysis failed: {str(e)}'}

    def print_quantstats_report(self, daily_returns: pd.Series):
        """Print formatted QuantStats report."""
        if not HAS_QUANTSTATS:
            print("⚠️  QuantStats not installed")
            return

        stats = self.analyze_with_quantstats(daily_returns)

        if 'error' in stats:
            print(f"❌ {stats['error']}")
            return

        print("\n" + "=" * 80)
        print("📊 QUANTSTATS ANALYTICS")
        print("=" * 80)
        print(f"\n📈 RETURNS:")
        print(f"  Total Return:        {stats['total_return']*100:7.2f}%")
        print(f"  Annual Return:       {stats['annual_return']*100:7.2f}%")
        print(f"  Best Day:            {stats['best_day']*100:7.2f}%")
        print(f"  Worst Day:           {stats['worst_day']*100:7.2f}%")

        print(f"\n📉 RISK METRICS:")
        print(f"  Volatility:          {stats['volatility']*100:7.2f}%")
        print(f"  Max Drawdown:        {stats['max_drawdown']*100:7.2f}%")
        print(f"  Avg Drawdown:        {stats['avg_drawdown']*100:7.2f}%")
        print(f"  Skewness:            {stats['skew']:7.2f}")
        print(f"  Kurtosis:            {stats['kurtosis']:7.2f}")

        print(f"\n⭐ RISK-ADJUSTED RETURNS:")
        print(f"  Sharpe Ratio:        {stats['sharpe']:7.2f}")
        print(f"  Sortino Ratio:       {stats['sortino']:7.2f}")
        print(f"  Calmar Ratio:        {stats['calmar']:7.2f}")
        print(f"  Win Rate:            {stats['win_rate']*100:7.2f}%")

        if 'beta' in stats:
            print(f"\n🎯 BENCHMARK COMPARISON:")
            print(f"  Beta:                {stats['beta']:7.2f}")
            print(f"  Alpha:               {stats['alpha']*100:7.2f}%")
            print(f"  Correlation:         {stats['correlation']:7.2f}")

        print("=" * 80)


def run_simple_backtest(trades_df: pd.DataFrame, initial_capital: float = 10000.0, fee_rate: float = 0.001, close_prices=None) -> SimplePortfolio:
    """Run backtest with simplified portfolio. Execute trades as planned during backtest, then rebalance at end."""

    portfolio = SimplePortfolio(initial_capital=initial_capital, fee_rate=fee_rate)

    # Process trades by date
    for date in sorted(trades_df['Date'].unique()):
        day_trades = trades_df[trades_df['Date'] == date]

        # Execute SELLS first
        # IMPORTANT: SELL ALL shares in tickers that are exiting top 5
        for _, trade in day_trades[day_trades['Type'] == 'SELL'].iterrows():
            ticker = trade['Ticker']
            price = float(str(trade['Price']).replace('€', '').strip())
            qty = int(trade['Quantity'])

            # Sell ALL shares in this ticker (it's exiting top 5)
            if ticker in portfolio.holdings:
                # Sell 100% of what we have, NOT just the planned qty
                actual_shares = portfolio.holdings[ticker]['shares']
                if actual_shares > 0:
                    portfolio.sell(date, ticker, price, actual_shares)

        # Execute BUYS
        for _, trade in day_trades[day_trades['Type'] == 'BUY'].iterrows():
            ticker = trade['Ticker']
            price = float(str(trade['Price']).replace('€', '').strip())
            qty = int(trade['Quantity'])

            portfolio.buy(date, ticker, price, qty)

    # FINAL REBALANCE: Deploy all remaining cash into equal-weight positions
    if close_prices is not None:
        final_date = close_prices.index[-1]

        # Current portfolio value at final prices
        final_value = portfolio.cash
        for ticker in portfolio.holdings:
            if ticker in close_prices.columns:
                price = close_prices[ticker].iloc[-1]
                final_value += portfolio.holdings[ticker]['shares'] * price

        # Target: 20% per position (equal weight across N positions)
        n_positions = len(portfolio.holdings) if len(portfolio.holdings) > 0 else 5
        if n_positions > 0:
            target_per_position = final_value / n_positions

            # Rebalance each position to target value
            for ticker in sorted(portfolio.holdings.keys()):
                if ticker in close_prices.columns:
                    price = close_prices[ticker].iloc[-1]
                    current_value = portfolio.holdings[ticker]['shares'] * price
                    target_value = target_per_position

                    if current_value < target_value:
                        # Buy more to reach target
                        amount_to_invest = target_value - current_value
                        qty_to_buy = int(amount_to_invest / price)

                        if qty_to_buy > 0 and qty_to_buy * price <= portfolio.cash:
                            portfolio.buy(final_date, ticker, price, qty_to_buy)

    return portfolio

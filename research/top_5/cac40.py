#!/usr/bin/env python3
"""
CAC40 Top 5 Momentum Backtest
- Daily momentum calculation (1-month window)
- Rebalance daily: SELL positions outside top 5, BUY new positions in top 5
- Track portfolio metrics with QuantStats
"""

import sys
sys.path.insert(0, '/Volumes/Data/dev/cresus/src')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import logging
import argparse
import time

from tools.portfolio import PortfolioManager
from agents.data import DataAgent
from tools.universe import Universe
from core.context import AgentContext

warnings.filterwarnings("ignore")

# Suppress loguru INFO logs
try:
    from loguru import logger
    logger.disable("tools.data")
except:
    pass

# Suppress INFO level logs
logging.getLogger().setLevel(logging.WARNING)

class CAC40MomentumBacktest:
    """Daily Top 5 momentum strategy for CAC40."""

    FEE_RATE = 0.0015  # 0.15% per order (buy and sell)

    def __init__(self, start_date: str = None, initial_capital: float = 10000.0, days_back: int = 365*2, show_trades: bool = False):
        """
        Initialize backtest.

        Args:
            start_date: Start date (YYYY-MM-DD), defaults to days_back ago
            initial_capital: Initial portfolio value in EUR
            days_back: Days to look back (default 2 years)
            show_trades: Print trades as they execute
        """
        self.initial_capital = initial_capital
        self.show_trades = show_trades

        # Dates
        if start_date:
            self.start_date = pd.to_datetime(start_date)
        else:
            self.start_date = datetime.now() - timedelta(days=days_back)

        self.end_date = datetime.now()

        print(f"📊 CAC40 TOP 5 MOMENTUM BACKTEST")
        print(f"   Period: {self.start_date.date()} to {self.end_date.date()}")
        print(f"   Initial Capital: €{initial_capital:,.0f}")
        print()

        # Load universe and data
        self._load_data()

    def _load_data(self):
        """Load CAC40 tickers and historical data using DataAgent."""
        print("📍 Loading CAC40 universe...")

        # Get tickers from universe
        universe = Universe('cac40')
        self.tickers = universe.get_tickers()
        print(f"✅ Loaded {len(self.tickers)} CAC40 tickers")

        # Use DataAgent to load price data
        print("📍 Loading price data via DataAgent...")
        context = AgentContext()
        data_agent = DataAgent(name="data_loader", context=context)
        result = data_agent.process(input_data={"tickers": self.tickers})

        if result.get("status") == "error":
            print(f"\n⚠️  ERROR: {result.get('message')}")
            sys.exit(1)

        # Extract price data from DataAgent result
        self.price_data = {}  # {ticker: price_series}
        data_history = data_agent.context.get("data_history") or {}

        if data_history:
            # Process all tickers at once
            for ticker, df in data_history.items():
                if df.empty or 'timestamp' not in df.columns or 'close' not in df.columns:
                    continue

                try:
                    # DataAgent returns data in descending order (newest first)
                    # Sort to ascending order for consistent momentum calculation
                    df = df.sort_values('timestamp', ascending=True).reset_index(drop=True)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])

                    # Extract price series and filter to backtest period
                    prices = df.set_index('timestamp')['close']
                    prices = prices[(prices.index >= self.start_date) & (prices.index <= self.end_date)]

                    if len(prices) > 20:
                        self.price_data[ticker] = prices
                except Exception:
                    continue

        print(f"✅ Loaded price data for {len(self.price_data)} tickers")

        if len(self.price_data) == 0:
            print("\n⚠️  ERROR: No price data loaded!")
            sys.exit(1)

        print(f"✅ All price data kept in memory for fast backtest access")

        # Build data_history indexed by date: {date: {ticker: price}}
        print("📍 Building data history index...")
        self.data_history = {}  # {date: {ticker: price}}

        for ticker, prices in self.price_data.items():
            for date in prices.index:
                if date not in self.data_history:
                    self.data_history[date] = {}
                self.data_history[date][ticker] = prices[date]

        print(f"✅ Indexed prices for {len(self.data_history)} dates")

        # Precompute momentum scores for all tickers on all dates
        print("📍 Precomputing momentum scores...")
        self.momentum_data = {}  # {ticker: {date: momentum_score}}

        for ticker, prices in self.price_data.items():
            self.momentum_data[ticker] = {}
            for date in prices.index:
                historical_prices = prices[prices.index <= date]
                if len(historical_prices) >= 22:  # Need at least 21 days + 1 reference
                    current = historical_prices.iloc[-1]
                    past = historical_prices.iloc[-22]
                    if past != 0:
                        momentum = ((current - past) / past) * 100
                        self.momentum_data[ticker][date] = momentum

        print(f"✅ Computed momentum for {len(self.momentum_data)} tickers")

    def _calculate_momentum(self, prices: pd.Series, lookback_days: int = 21) -> float:
        """
        Calculate 1-month momentum (21-day lookback).

        Returns:
            Momentum as percentage change
        """
        if len(prices) < lookback_days + 1:
            return 0.0

        current = prices.iloc[-1]
        past = prices.iloc[-lookback_days - 1]

        if past == 0:
            return 0.0

        return ((current - past) / past) * 100

    def build_watchlist(self, date: pd.Timestamp) -> pd.DataFrame:
        """Build watchlist with prices for current date."""
        current_data = self.data_history.get(date, {})
        if not current_data:
            return pd.DataFrame()

        watchlist_data = [
            {'ticker': ticker, 'close': price}
            for ticker, price in current_data.items()
        ]
        return pd.DataFrame(watchlist_data).reset_index(drop=True)


    def run_backtest(self):
        """Run daily backtest using PortfolioManager."""
        print("\n📍 Running daily backtest with PortfolioManager...")

        # Nested functions for watchlist processing
        def watchlist_scoring(watchlist: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
            """Add score column to watchlist from precomputed momentum."""
            if watchlist.empty:
                return watchlist

            scores = []
            for _, row in watchlist.iterrows():
                ticker = row['ticker']
                if ticker in self.momentum_data and date in self.momentum_data[ticker]:
                    score = self.momentum_data[ticker][date]
                else:
                    score = 0.0
                scores.append(score)

            watchlist['score'] = scores
            return watchlist

        def watchlist_ranking(watchlist: pd.DataFrame) -> list:
            """Rank tickers by score (highest first)."""
            if watchlist.empty or 'score' not in watchlist.columns:
                return []
            sorted_wl = watchlist.sort_values(['score', 'ticker'], ascending=[False, True])
            return sorted_wl['ticker'].tolist()

        def watchlist_filter(ranked_tickers: list, top_n: int = 5) -> list:
            """Filter to top N tickers from ranked list."""
            return ranked_tickers[:top_n] if len(ranked_tickers) >= top_n else []

        # Create fresh portfolio in PortfolioManager
        portfolio_name = f"cac40_momentum_{self.start_date.strftime('%Y%m%d')}"
        self.pm = PortfolioManager(context={})

        # Delete existing portfolio if it exists to start fresh
        try:
            self.pm.delete_portfolio(portfolio_name)
        except Exception:
            pass  # Portfolio doesn't exist yet

        # Create fresh portfolio
        self.pm.create_portfolio(
            name=portfolio_name,
            portfolio_type="paper",
            initial_capital=self.initial_capital,
            currency="EUR",
            description="CAC40 Top 5 Momentum Strategy"
        )
        print(f"📊 Created fresh portfolio: {portfolio_name}")

        # Get unique dates from price data
        all_dates = set()
        for prices in self.price_data.values():
            all_dates.update(prices.index)

        sorted_dates = sorted(all_dates)
        print(f"📊 Processing {len(sorted_dates)} trading days...")

        rebalance_count = 0
        last_rebalance_date = None
        portfolio_values = []
        portfolio_dates = []

        # Timing instrumentation
        timings = {
            'rebalance_check': 0,
            'top5_calc': 0,
            'price_lookup': 0,
            'trade_exec': 0,
            'portfolio_update': 0,
        }

        # Process each trading day
        for idx, date in enumerate(sorted_dates):
            t_start = time.perf_counter()
            # Only rebalance on Mondays (weekday() == 0)
            if last_rebalance_date is None:
                should_rebalance = True  # First day
            else:
                # Rebalance if it's been 7 calendar days
                should_rebalance = (date - last_rebalance_date).days >= 7

            t_rebalance_check = time.perf_counter()
            timings['rebalance_check'] += t_rebalance_check - t_start

            if not should_rebalance:
                continue

            t_top5_start = time.perf_counter()
            # Get top 5 momentum tickers: score → rank → filter
            watchlist_df = self.build_watchlist(date)
            if not watchlist_df.empty:
                watchlist_df = watchlist_scoring(watchlist_df, date)
                ranked_tickers = watchlist_ranking(watchlist_df)
                watchlist = watchlist_filter(ranked_tickers, top_n=5)
            else:
                watchlist = []
            timings['top5_calc'] += time.perf_counter() - t_top5_start
            if len(watchlist) < 5:
                continue  # Skip if insufficient data

            top_5_set = set(watchlist)

            # Get current holdings from PortfolioManager
            positions = self.pm.get_portfolio_positions(portfolio_name) or {}
            current_holdings = {p['ticker']: p['quantity'] for p in positions.get('positions', [])}

            # Identify positions to close and open (sorted for deterministic order)
            to_close = sorted(set(current_holdings.keys()) - top_5_set)
            to_open = sorted(top_5_set - set(current_holdings.keys()))

            # Track rebalances
            if to_close or to_open:
                rebalance_count += 1
                last_rebalance_date = date

            # Get prices from data_history for current date
            t_price_start = time.perf_counter()
            current_data = self.data_history.get(date, {})
            timings['price_lookup'] += time.perf_counter() - t_price_start

            t_trade_start = time.perf_counter()
            # SELL positions exiting top 5
            for ticker in to_close:
                if ticker in current_data and ticker in current_holdings:
                    qty = current_holdings[ticker]
                    price = current_data[ticker]
                    fees = qty * price * self.FEE_RATE
                    proceeds = qty * price - fees

                    if self.show_trades:
                        print(f"  {date.date()} SELL {ticker:8} {qty:6} @ €{price:8.2f} = €{qty * price:9.2f} - €{fees:7.2f} fees")

                    self.pm.record_transaction(
                        portfolio_name=portfolio_name,
                        operation="SELL",
                        ticker=ticker,
                        quantity=qty,
                        price=price,
                        fees=fees,
                        created_at=date.isoformat()
                    )

                    del current_holdings[ticker]

            # BUY positions entering top 5
            if to_open:
                # Get cash from PortfolioManager (source of truth)
                cash = self.pm.get_portfolio_cash(portfolio_name)
                # Calculate portfolio value from current holdings + cash
                position_value = sum(current_holdings.get(t, 0) * current_data.get(t, 0) for t in current_holdings.keys() if t in current_data)
                portfolio_value = cash + position_value
                target_per_position = portfolio_value * 0.20

                for ticker in to_open:
                    if ticker in current_data:
                        price = current_data[ticker]
                        qty = int(target_per_position / (price * (1 + self.FEE_RATE)))

                        if qty > 0:
                            fees = qty * price * self.FEE_RATE
                            cost = qty * price + fees

                            if cost <= cash:
                                if self.show_trades:
                                    print(f"  {date.date()} BUY  {ticker:8} {qty:6} @ €{price:8.2f} = €{qty * price:9.2f} + €{fees:7.2f} fees")

                                self.pm.record_transaction(
                                    portfolio_name=portfolio_name,
                                    operation="BUY",
                                    ticker=ticker,
                                    quantity=qty,
                                    price=price,
                                    fees=fees,
                                    created_at=date.isoformat()
                                )

                                current_holdings[ticker] = qty

            timings['trade_exec'] += time.perf_counter() - t_trade_start

            t_portfolio_start = time.perf_counter()
            # Track portfolio value from PortfolioManager cash + current holdings
            cash = self.pm.get_portfolio_cash(portfolio_name)
            position_value = sum(current_holdings.get(t, 0) * current_data.get(t, 0) for t in current_holdings.keys() if t in current_data)
            portfolio_value = cash + position_value
            portfolio_values.append(portfolio_value)
            portfolio_dates.append(date)

            timings['portfolio_update'] += time.perf_counter() - t_portfolio_start

            # Progress indicator
            if (idx + 1) % 252 == 0:  # ~1 year of trading days
                years_elapsed = (idx + 1) / 252
                print(f"  ✅ Year {years_elapsed:.1f}: {len(current_holdings)} positions, value: €{portfolio_value:,.0f}")

        # Store results
        self.portfolio_name = portfolio_name
        self.rebalance_count = rebalance_count
        self.final_holdings = current_holdings
        self.final_portfolio_value = portfolio_values[-1] if portfolio_values else self.initial_capital
        self.portfolio_values = pd.Series(portfolio_values, index=portfolio_dates)

        # Get trades from PortfolioManager (authoritative source)
        transactions_data = self.pm.get_portfolio_transactions(portfolio_name)
        self.trade_count = len(transactions_data.get('transactions', []))

        # Get authoritative cash from PortfolioManager (calculated from journal)
        self.cash = self.pm.get_portfolio_cash(portfolio_name)
        print(f"✅ Cash verified from journal: €{self.cash:.2f}")

        # Report timing breakdown
        total_time = sum(timings.values())
        print(f"\n✅ Backtest complete")
        print(f"   Trades executed: {self.trade_count}")
        print(f"   Final holdings: {len(self.final_holdings)} positions")
        print(f"   Portfolio value: €{self.final_portfolio_value:,.2f}")
        print(f"\n⏱️  Timing breakdown (total: {total_time:.2f}s):")
        for phase, duration in sorted(timings.items(), key=lambda x: x[1], reverse=True):
            pct = (duration / total_time * 100) if total_time > 0 else 0
            print(f"   {phase:20} {duration:8.3f}s ({pct:5.1f}%)")

        return self

    def show_metrics(self):
        """Display portfolio metrics from PortfolioManager."""
        print("\n" + "="*100)
        print("📊 PORTFOLIO METRICS - CAC40 TOP 5 MOMENTUM STRATEGY")
        print("="*100)

        print(f"\n📅 PERIOD:")
        print(f"  Start Date:            {self.start_date.date()}")
        print(f"  End Date:              {self.end_date.date()}")
        print(f"  Duration:              {(self.end_date - self.start_date).days} days")

        print(f"\n💰 CAPITAL:")
        print(f"  Initial Capital:       €{self.initial_capital:,.2f}")
        print(f"  Final Value:           €{self.final_portfolio_value:,.2f}")
        print(f"  Cash Remaining:        €{self.cash:,.2f}")
        total_return_pct = ((self.final_portfolio_value - self.initial_capital) / self.initial_capital * 100)
        print(f"  Total Return:          {total_return_pct:+.2f}%")

        print(f"\n🎯 TRADING ACTIVITY:")
        print(f"  Total Trades:          {self.trade_count}")
        transactions = self.pm.get_portfolio_transactions(self.portfolio_name).get('transactions', [])
        buys = len([t for t in transactions if t.get('operation') == 'BUY'])
        sells = len([t for t in transactions if t.get('operation') == 'SELL'])
        print(f"  Buys:                  {buys}")
        print(f"  Sells:                 {sells}")
        print(f"  Rebalances:            {self.rebalance_count}")

        print(f"\n📌 CURRENT HOLDINGS ({len(self.final_holdings)}/5):")
        if self.final_holdings:
            # Try to get latest prices from price_data
            total_position_value = 0
            for ticker in self.final_holdings:
                if ticker in self.price_data and len(self.price_data[ticker]) > 0:
                    price = self.price_data[ticker].iloc[-1]
                    if pd.notna(price) and price > 0:
                        total_position_value += self.final_holdings[ticker] * price

            for i, (ticker, qty) in enumerate(sorted(self.final_holdings.items()), 1):
                if ticker in self.price_data and len(self.price_data[ticker]) > 0:
                    latest_price = self.price_data[ticker].iloc[-1]
                    if pd.notna(latest_price) and latest_price > 0:
                        position_value = qty * latest_price
                        pct_of_portfolio = (position_value / self.final_portfolio_value * 100) if self.final_portfolio_value > 0 else 0
                        print(f"  {i}. {ticker:8} {qty:6.0f} shares @ €{latest_price:7.2f} = €{position_value:9,.2f} ({pct_of_portfolio:5.1f}%)")
                    else:
                        print(f"  {i}. {ticker:8} {qty:6.0f} shares @ € (price N/A)")
                else:
                    print(f"  {i}. {ticker:8} {qty:6.0f} shares @ € (no price data)")
        else:
            print("  No open positions")

        print("\n" + "="*100)
        print("ℹ️  For detailed QuantStats metrics:")
        print(f"    metrics = pm.calculate_backtest_metrics('{self.portfolio_name}')")
        print("="*100)

    def summary(self) -> dict:
        """Return backtest summary."""
        return {
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "days": (self.end_date - self.start_date).days,
            "initial_capital": self.initial_capital,
            "rebalances": self.rebalance_count,
            "trades": self.trade_count,
            "final_holdings": list(self.final_holdings),
            "data_sources": {
                "tickers_loaded": len(self.price_data),
            }
        }


def main():
    """Run CAC40 Top 5 Momentum backtest."""
    parser = argparse.ArgumentParser(description="CAC40 Top 5 Momentum Backtest")
    parser.add_argument("--trades", action="store_true", help="Show individual trades as they execute")
    args = parser.parse_args()

    # Initialize backtest (last 2 years)
    backtest = CAC40MomentumBacktest(initial_capital=10000.0, show_trades=args.trades)

    # Run backtest
    backtest.run_backtest()

    # Display metrics
    backtest.show_metrics()

    # Print summary
    summary = backtest.summary()
    print("\n📋 BACKTEST SUMMARY:")
    print(f"  Period: {summary['start_date']} to {summary['end_date']} ({summary['days']} days)")
    print(f"  Rebalances: {summary['rebalances']}")
    print(f"  Trades: {summary['trades']}")
    print(f"  Data: {summary['data_sources']['tickers_loaded']} tickers loaded")

    return backtest


if __name__ == "__main__":
    backtest = main()

"""
Tests for portfolio engine.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from portfolio_engine import PortfolioEngine, run_portfolio_backtest


def test_simple_buy_sell():
    """Test basic buy then sell."""
    portfolio = PortfolioEngine(initial_capital=10000.0, fee_rate=0.005)
    portfolio.add_cash(datetime(2020, 1, 1), 10000.0)

    # Buy 100 shares @ €50
    assert portfolio.buy(datetime(2020, 1, 1), "TEST", 50.0, 100)
    assert portfolio.cash == 10000.0 - (50.0 * 100 + 50.0 * 100 * 0.005)  # Cost + fees
    assert len(portfolio.positions) == 1

    # Sell 100 shares @ €60
    success, pnl_list = portfolio.sell(datetime(2020, 1, 2), "TEST", 60.0, 100)
    assert success
    assert len(pnl_list) == 1
    assert pnl_list[0] == pytest.approx(20.0, rel=0.1)  # Should be ~20% gain
    assert portfolio.positions == []  # All closed
    print("✅ test_simple_buy_sell PASSED")


def test_insufficient_cash():
    """Test buy fails when insufficient cash."""
    portfolio = PortfolioEngine(initial_capital=100.0)

    # Try to buy €1000 worth
    assert not portfolio.buy(datetime(2020, 1, 1), "TEST", 50.0, 100)
    assert len(portfolio.positions) == 0
    print("✅ test_insufficient_cash PASSED")


def test_fifo_matching():
    """Test FIFO matching with multiple buy orders."""
    portfolio = PortfolioEngine(initial_capital=50000.0)
    portfolio.add_cash(datetime(2020, 1, 1), 50000.0)

    # Buy 100 @ €50
    portfolio.buy(datetime(2020, 1, 1), "TEST", 50.0, 100)
    # Buy 100 @ €55
    portfolio.buy(datetime(2020, 1, 2), "TEST", 55.0, 100)
    assert len(portfolio.positions) == 2
    assert sum(p.quantity for p in portfolio.positions) == 200

    # Sell 150 (FIFO: 100 @ €50, 50 @ €55)
    success, pnl_list = portfolio.sell(datetime(2020, 1, 3), "TEST", 60.0, 150)
    assert success
    assert len(pnl_list) == 2  # Two positions matched
    assert len(portfolio.positions) == 1  # One position remains with 50 shares
    assert portfolio.positions[0].quantity == 50
    print("✅ test_fifo_matching PASSED")


def test_cannot_sell_more_than_owned():
    """Test cannot sell more shares than owned."""
    portfolio = PortfolioEngine(initial_capital=10000.0)
    portfolio.add_cash(datetime(2020, 1, 1), 10000.0)

    portfolio.buy(datetime(2020, 1, 1), "TEST", 50.0, 100)

    # Try to sell 200 (only have 100)
    success, pnl_list = portfolio.sell(datetime(2020, 1, 2), "TEST", 60.0, 200)
    assert not success
    assert len(portfolio.positions) == 1  # Still have position
    print("✅ test_cannot_sell_more_than_owned PASSED")


def test_fee_calculation():
    """Test fees are calculated correctly."""
    portfolio = PortfolioEngine(initial_capital=10000.0, fee_rate=0.005)

    # Buy 100 @ €50
    cost = 50.0 * 100 * (1 + 0.005)  # €5,025
    assert portfolio.buy(datetime(2020, 1, 1), "TEST", 50.0, 100)

    # Sell 100 @ €60
    proceeds = 60.0 * 100 * (1 - 0.005)  # €5,970
    portfolio.sell(datetime(2020, 1, 2), "TEST", 60.0, 100)

    total_fees = (50.0 * 100 * 0.005) + (60.0 * 100 * 0.005)
    expected_cash = 10000.0 - cost + proceeds
    assert portfolio.cash == pytest.approx(expected_cash, rel=0.001)
    print("✅ test_fee_calculation PASSED")


def test_multiple_positions_different_tickers():
    """Test holding multiple positions in different tickers."""
    portfolio = PortfolioEngine(initial_capital=50000.0)
    portfolio.add_cash(datetime(2020, 1, 1), 50000.0)

    # Buy TICK1
    portfolio.buy(datetime(2020, 1, 1), "TICK1", 100.0, 100)
    # Buy TICK2
    portfolio.buy(datetime(2020, 1, 1), "TICK2", 50.0, 100)

    assert len(portfolio.positions) == 2

    # Sell TICK1 only
    success, _ = portfolio.sell(datetime(2020, 1, 2), "TICK1", 110.0, 100)
    assert success
    assert len(portfolio.positions) == 1
    assert portfolio.positions[0].ticker == "TICK2"
    print("✅ test_multiple_positions_different_tickers PASSED")


def test_metrics_calculation():
    """Test portfolio metrics are calculated correctly."""
    portfolio = PortfolioEngine(initial_capital=10000.0)
    portfolio.add_cash(datetime(2020, 1, 1), 10000.0)

    # Trade 1: Buy @ €50, Sell @ €60 (20% gain)
    portfolio.buy(datetime(2020, 1, 1), "TEST", 50.0, 100)
    portfolio.sell(datetime(2020, 1, 2), "TEST", 60.0, 100)

    # Trade 2: Buy @ €60, Sell @ €50 (16.7% loss)
    portfolio.buy(datetime(2020, 1, 3), "TEST", 60.0, 100)
    portfolio.sell(datetime(2020, 1, 4), "TEST", 50.0, 100)

    metrics = portfolio.get_metrics()
    assert metrics['total_trades'] == 2
    assert metrics['closed_trades'] == 2
    assert metrics['win_rate'] == 50.0  # 1 win, 1 loss
    print("✅ test_metrics_calculation PASSED")


if __name__ == "__main__":
    import pytest

    # Run tests
    test_simple_buy_sell()
    test_insufficient_cash()
    test_fifo_matching()
    test_cannot_sell_more_than_owned()
    test_fee_calculation()
    test_multiple_positions_different_tickers()
    test_metrics_calculation()

    print("\n" + "=" * 80)
    print("✅ ALL PORTFOLIO ENGINE TESTS PASSED")
    print("=" * 80)

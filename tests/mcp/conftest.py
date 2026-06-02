"""Pytest configuration for MCP tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import httpx
from src.mcp.domains.portfolio import PortfolioDomain


@pytest.fixture
def mock_client():
    """Create a mock httpx AsyncClient."""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
def portfolio_domain(mock_client):
    """Create a PortfolioDomain with mock client."""
    return PortfolioDomain(mock_client)


@pytest.fixture
def sample_portfolio():
    """Sample portfolio data."""
    return {
        "status": "success",
        "portfolio": {
            "name": "Main",
            "type": "paper",
            "currency": "EUR",
            "initial_capital": 100000.0,
            "current_value": 125000.0,
            "cash": 25000.0,
            "invested": 100000.0,
            "return": 0.25,
        },
    }


@pytest.fixture
def sample_positions():
    """Sample portfolio positions."""
    return {
        "status": "success",
        "positions": [
            {
                "ticker": "AAPL",
                "quantity": 10,
                "entry_price": 150.0,
                "current_price": 175.0,
                "pnl": 250.0,
                "pnl_pct": 0.167,
            },
            {
                "ticker": "GOOGL",
                "quantity": 5,
                "entry_price": 140.0,
                "current_price": 165.0,
                "pnl": 125.0,
                "pnl_pct": 0.179,
            },
        ],
        "total": 2,
    }


@pytest.fixture
def sample_metrics():
    """Sample portfolio metrics."""
    return {
        "status": "success",
        "metrics": {
            "sharpe_ratio": 1.45,
            "sortino_ratio": 2.15,
            "max_drawdown": -0.12,
            "volatility": 0.18,
            "return": 0.25,
            "win_rate": 0.65,
            "total_trades": 20,
        },
    }


@pytest.fixture
def sample_transactions():
    """Sample portfolio transactions."""
    return {
        "status": "success",
        "transactions": [
            {
                "date": "2024-01-15",
                "type": "BUY",
                "ticker": "AAPL",
                "quantity": 10,
                "price": 150.0,
                "fees": 10.0,
                "total": 1510.0,
            },
            {
                "date": "2024-01-20",
                "type": "BUY",
                "ticker": "GOOGL",
                "quantity": 5,
                "price": 140.0,
                "fees": 7.0,
                "total": 707.0,
            },
        ],
        "total": 2,
    }

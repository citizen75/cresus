"""Tests for /portfolios endpoints.

api.routes.portfolios caches PortfolioManager/PortfolioMetrics/BotManager via
@lru_cache(maxsize=1) - cleared per test below, same pattern as test_bots.py.

Endpoints that price open positions (get_portfolio_details/positions,
current-prices, value, refresh) call out to tools.data (Fundamental/
DataHistory) for live or cached price lookups - tests with actual positions
mock those; tests against a position-less portfolio don't need to (the
pricing loop never runs over zero rows).
"""

from unittest.mock import patch

import pytest

from api.routes import portfolios as portfolios_module
from api.routes.portfolios import router


@pytest.fixture(autouse=True)
def _clear_portfolio_manager_caches():
    portfolios_module._get_portfolio_manager.cache_clear()
    portfolios_module._get_metrics.cache_clear()
    portfolios_module._get_bot_manager.cache_clear()
    yield
    portfolios_module._get_portfolio_manager.cache_clear()
    portfolios_module._get_metrics.cache_clear()
    portfolios_module._get_bot_manager.cache_clear()


def _create_portfolio(client, name="ptf_a", **kw):
    payload = {"name": name}
    payload.update(kw)
    return client.post("/api/v1/portfolios", json=payload)


def test_list_portfolios_empty(make_client):
    client = make_client(router)
    response = client.get("/api/v1/portfolios")
    assert response.status_code == 200
    data = response.json()
    assert data["portfolios"] == []
    assert data["total"] == 0


def test_create_portfolio(make_client):
    client = make_client(router)
    response = _create_portfolio(client, initial_capital=50000.0, currency="USD")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["portfolio"]["name"] == "ptf_a"
    assert data["portfolio"]["initial_capital"] == 50000.0
    assert data["portfolio"]["currency"] == "USD"


def test_create_duplicate_portfolio_400(make_client):
    client = make_client(router)
    _create_portfolio(client)
    response = _create_portfolio(client)
    assert response.status_code == 400


def test_get_portfolio_metadata(make_client):
    client = make_client(router)
    _create_portfolio(client)

    response = client.get("/api/v1/portfolios/ptf_a/metadata")
    assert response.status_code == 200
    assert response.json()["name"] == "ptf_a"


def test_get_metadata_missing_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/portfolios/ghost/metadata")
    assert response.status_code == 404


def test_get_portfolio_details_empty(make_client):
    client = make_client(router)
    _create_portfolio(client)

    response = client.get("/api/v1/portfolios/ptf_a")
    assert response.status_code == 200
    data = response.json()
    assert data["num_positions"] == 0
    assert data["positions"] == []
    assert data["total_value"] == 0


def test_get_details_missing_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/portfolios/ghost")
    assert response.status_code == 404


def test_list_portfolios_after_create(make_client):
    client = make_client(router)
    _create_portfolio(client, name="ptf_1")
    _create_portfolio(client, name="ptf_2")

    response = client.get("/api/v1/portfolios")
    data = response.json()
    assert data["total"] == 2


def test_update_portfolio(make_client):
    client = make_client(router)
    _create_portfolio(client)

    response = client.put(
        "/api/v1/portfolios/ptf_a", json={"description": "Updated desc", "currency": "USD"}
    )
    assert response.status_code == 200

    metadata = client.get("/api/v1/portfolios/ptf_a/metadata").json()
    assert metadata["description"] == "Updated desc"
    assert metadata["currency"] == "USD"


def test_delete_portfolio(make_client):
    client = make_client(router)
    _create_portfolio(client)

    response = client.delete("/api/v1/portfolios/ptf_a")
    assert response.status_code == 200
    assert client.get("/api/v1/portfolios/ptf_a").status_code == 404


def test_delete_missing_portfolio_404(make_client):
    client = make_client(router)
    response = client.delete("/api/v1/portfolios/ghost")
    assert response.status_code == 404


def test_get_positions_empty(make_client):
    client = make_client(router)
    _create_portfolio(client)

    response = client.get("/api/v1/portfolios/ptf_a/positions")
    assert response.status_code == 200
    data = response.json()
    assert data["positions"] == []
    assert data["total_value"] == 0


def test_record_cash_deposit(make_client):
    client = make_client(router)
    _create_portfolio(client)

    response = client.post(
        "/api/v1/portfolios/ptf_a/transactions",
        json={"operation": "CASH", "quantity": 1000},
    )
    assert response.status_code == 200

    txns = client.get("/api/v1/portfolios/ptf_a/transactions").json()
    assert txns["total_count"] == 1
    assert txns["transactions"][0]["operation"] == "CASH"


def test_record_buy_and_sell_transaction(make_client):
    client = make_client(router)
    _create_portfolio(client)

    with patch("tools.data.Fundamental") as MockFundamental, patch(
        "tools.data.DataHistory"
    ) as MockHistory:
        MockFundamental.return_value.get_current_price.return_value = 160.0
        MockFundamental.return_value.get_company_info.return_value = {"company_name": "Apple"}
        MockHistory.return_value.get_current_price.return_value = 160.0

        buy_resp = client.post(
            "/api/v1/portfolios/ptf_a/transactions",
            json={"operation": "BUY", "ticker": "AAPL", "quantity": 10, "price": 150.0},
        )
        assert buy_resp.status_code == 200

        positions = client.get("/api/v1/portfolios/ptf_a/positions").json()
        assert positions["positions"][0]["ticker"] == "AAPL"
        assert positions["positions"][0]["quantity"] == 10

        sell_resp = client.post(
            "/api/v1/portfolios/ptf_a/transactions",
            json={"operation": "SELL", "ticker": "AAPL", "quantity": 10, "price": 160.0},
        )
        assert sell_resp.status_code == 200

    positions_after = client.get("/api/v1/portfolios/ptf_a/positions").json()
    assert positions_after["positions"] == []


def test_get_transactions_filtered_by_ticker(make_client):
    client = make_client(router)
    _create_portfolio(client)
    client.post(
        "/api/v1/portfolios/ptf_a/transactions",
        json={"operation": "CASH", "quantity": 1000},
    )

    with patch("tools.data.Fundamental") as MockFundamental, patch("tools.data.DataHistory") as MockHistory:
        MockFundamental.return_value.get_current_price.return_value = 100.0
        MockFundamental.return_value.get_company_info.return_value = {"company_name": "X"}
        MockHistory.return_value.get_current_price.return_value = 100.0
        client.post(
            "/api/v1/portfolios/ptf_a/transactions",
            json={"operation": "BUY", "ticker": "AAPL", "quantity": 1, "price": 100.0},
        )

    response = client.get("/api/v1/portfolios/ptf_a/transactions?ticker=AAPL")
    data = response.json()
    assert data["total_count"] == 1
    assert data["ticker_filter"] == "AAPL"


def test_update_transaction(make_client):
    client = make_client(router)
    _create_portfolio(client)
    client.post(
        "/api/v1/portfolios/ptf_a/transactions",
        json={"operation": "CASH", "quantity": 1000},
    )
    txn_id = client.get("/api/v1/portfolios/ptf_a/transactions").json()["transactions"][0]["id"]

    response = client.put(
        f"/api/v1/portfolios/ptf_a/transactions/{txn_id}",
        json={"notes": "adjusted"},
    )
    assert response.status_code == 200

    txn = client.get("/api/v1/portfolios/ptf_a/transactions").json()["transactions"][0]
    assert txn["notes"] == "adjusted"


def test_update_missing_transaction_400(make_client):
    client = make_client(router)
    _create_portfolio(client)
    response = client.put(
        "/api/v1/portfolios/ptf_a/transactions/does-not-exist", json={"notes": "x"}
    )
    assert response.status_code == 400


def test_delete_transaction(make_client):
    client = make_client(router)
    _create_portfolio(client)
    client.post(
        "/api/v1/portfolios/ptf_a/transactions",
        json={"operation": "CASH", "quantity": 1000},
    )
    txn_id = client.get("/api/v1/portfolios/ptf_a/transactions").json()["transactions"][0]["id"]

    response = client.delete(f"/api/v1/portfolios/ptf_a/transactions/{txn_id}")
    assert response.status_code == 200
    assert client.get("/api/v1/portfolios/ptf_a/transactions").json()["total_count"] == 0


def test_get_orders_empty(make_client):
    client = make_client(router)
    _create_portfolio(client)

    response = client.get("/api/v1/portfolios/ptf_a/orders")
    assert response.status_code == 200


def test_get_performance_empty_portfolio(make_client):
    client = make_client(router)
    _create_portfolio(client)

    response = client.get("/api/v1/portfolios/ptf_a/performance")
    assert response.status_code == 200
    data = response.json()
    assert data["num_trades"] == 0


def test_get_allocation_empty(make_client):
    client = make_client(router)
    _create_portfolio(client)

    response = client.get("/api/v1/portfolios/ptf_a/allocation")
    assert response.status_code == 200


def test_get_top_holdings_empty(make_client):
    client = make_client(router)
    _create_portfolio(client)

    response = client.get("/api/v1/portfolios/ptf_a/holdings")
    assert response.status_code == 200


def test_get_strategy_static_payload(make_client):
    client = make_client(router)
    _create_portfolio(client)

    response = client.get("/api/v1/portfolios/ptf_a/strategy")
    assert response.status_code == 200
    assert response.json()["name"] == "ptf_a"


def test_get_strategy_missing_portfolio_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/portfolios/ghost/strategy")
    assert response.status_code == 404


def test_get_backtest_static_payload(make_client):
    client = make_client(router)
    _create_portfolio(client)

    response = client.get("/api/v1/portfolios/ptf_a/backtest")
    assert response.status_code == 200
    assert "summary" in response.json()


def test_get_watchlist_no_strategy_file(make_client):
    client = make_client(router)
    _create_portfolio(client)

    response = client.get("/api/v1/portfolios/ptf_a/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert data["watchlist"] == []
    assert data["total_stocks"] == 0


def test_get_watchlist_missing_portfolio_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/portfolios/ghost/watchlist")
    assert response.status_code == 404


def test_get_current_prices_empty_portfolio(make_client):
    client = make_client(router)
    _create_portfolio(client)

    response = client.get("/api/v1/portfolios/ptf_a/current-prices")
    assert response.status_code == 200
    data = response.json()
    assert data["positions"] == []
    # No CASH transaction recorded yet - cash balance defaults to initial_capital.
    assert data["cash"] == 100000.0
    assert response.headers["cache-control"] == "public, max-age=300"


def test_get_current_prices_missing_portfolio_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/portfolios/ghost/current-prices")
    assert response.status_code == 404


def test_get_value(make_client):
    client = make_client(router)
    _create_portfolio(client, initial_capital=10000.0)
    client.post(
        "/api/v1/portfolios/ptf_a/transactions",
        json={"operation": "CASH", "quantity": 10000},
    )

    response = client.get("/api/v1/portfolios/ptf_a/value")
    assert response.status_code == 200


def test_get_value_missing_portfolio_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/portfolios/ghost/value")
    assert response.status_code == 404


def test_get_metrics_missing_portfolio_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/portfolios/ghost/metrics")
    assert response.status_code == 404


def test_get_cache_all(make_client):
    client = make_client(router)
    _create_portfolio(client)

    response = client.get("/api/v1/portfolios/cache/all")
    assert response.status_code == 200
    assert "cached_portfolios" in response.json()

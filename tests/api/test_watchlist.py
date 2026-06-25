"""Tests for /watchlists endpoints.

WatchlistManager(strategy_name) (no bot_dir/backtest_dir/portfolio_name) reads
CSV files from {CRESUS_HOME}/.cresus/db/watchlist/{strategy_name}.csv -
isolated per test by the autouse isolated_cresus_home fixture.

_get_ticker_metadata() and the /historical endpoint both call out to
tools.data (Fundamental/DataHistory), which the src/api CLAUDE.local.md says
must route through src/tools/data rather than calling yfinance directly in
route code (already the case here) - for tests we mock those two entry
points rather than hitting real network/cache.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from api.routes.watchlist import router


def _watchlist_path(isolated_cresus_home: Path, strategy_name: str) -> Path:
    path = isolated_cresus_home / ".cresus" / "db" / "watchlist"
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{strategy_name}.csv"


def _write_watchlist(isolated_cresus_home, strategy_name, rows):
    path = _watchlist_path(isolated_cresus_home, strategy_name)
    pd.DataFrame(rows).to_csv(path, index=False)


def test_list_watchlists_empty(make_client):
    client = make_client(router)
    response = client.get("/api/v1/watchlists")
    assert response.status_code == 200
    assert response.json() == {"watchlists": [], "count": 0}


def test_list_watchlists(make_client, isolated_cresus_home):
    _write_watchlist(isolated_cresus_home, "ta_cac_1", [{"ticker": "AAPL"}])
    _write_watchlist(isolated_cresus_home, "ta_cac_2", [{"ticker": "MSFT"}])

    client = make_client(router)
    response = client.get("/api/v1/watchlists")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert set(data["watchlists"]) == {"ta_cac_1", "ta_cac_2"}


def test_get_watchlist_not_found_returns_empty(make_client, isolated_cresus_home):
    client = make_client(router)
    response = client.get("/api/v1/watchlists/no_such_strategy")
    assert response.status_code == 200
    data = response.json()
    assert data["watchlist"] == []
    assert data["count"] == 0


def test_get_watchlist_sorted_by_score(make_client, isolated_cresus_home):
    _write_watchlist(
        isolated_cresus_home,
        "ta_cac_1",
        [
            {"ticker": "AAPL", "signal_score": 0.3},
            {"ticker": "MSFT", "signal_score": 0.9},
        ],
    )

    client = make_client(router)
    response = client.get("/api/v1/watchlists/ta_cac_1")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert data["watchlist"][0]["ticker"] == "MSFT"
    assert data["total_score"] == pytest.approx(1.2)


def test_get_watchlist_with_limit(make_client, isolated_cresus_home):
    _write_watchlist(
        isolated_cresus_home,
        "ta_cac_1",
        [{"ticker": t, "signal_score": i} for i, t in enumerate(["A", "B", "C"])],
    )

    client = make_client(router)
    response = client.get("/api/v1/watchlists/ta_cac_1?limit=1")
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_get_top_tickers(make_client, isolated_cresus_home):
    _write_watchlist(
        isolated_cresus_home,
        "ta_cac_1",
        [
            {"ticker": "AAPL", "close": 150.0, "signal_score": 0.3, "signals": ""},
            {"ticker": "MSFT", "close": 300.0, "signal_score": 0.9, "signals": ""},
        ],
    )

    client = make_client(router)
    response = client.get("/api/v1/watchlists/ta_cac_1/top?n=1")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["top_tickers"][0]["ticker"] == "MSFT"


def test_get_top_tickers_missing_watchlist_404(make_client, isolated_cresus_home):
    client = make_client(router)
    response = client.get("/api/v1/watchlists/no_such_strategy/top")
    assert response.status_code == 404


def test_get_watchlist_tickers(make_client, isolated_cresus_home):
    _write_watchlist(
        isolated_cresus_home, "ta_cac_1", [{"ticker": "AAPL"}, {"ticker": "MSFT"}]
    )

    client = make_client(router)
    response = client.get("/api/v1/watchlists/ta_cac_1/tickers")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert set(data["tickers"]) == {"AAPL", "MSFT"}


def test_add_ticker_to_watchlist(make_client, isolated_cresus_home):
    client = make_client(router)
    with patch("api.routes.watchlist.Fundamental") as MockFundamental:
        instance = MockFundamental.return_value
        instance.get_company_info.return_value = {"company_name": "Apple Inc."}
        instance.get_current_price.return_value = 150.0

        response = client.post(
            "/api/v1/watchlists/ta_cac_1/add", json={"ticker": "AAPL"}
        )
    assert response.status_code == 200
    assert response.json()["success"] is True

    tickers_resp = client.get("/api/v1/watchlists/ta_cac_1/tickers")
    assert tickers_resp.json()["tickers"] == ["AAPL"]


def test_add_duplicate_ticker_rejected(make_client, isolated_cresus_home):
    client = make_client(router)
    with patch("api.routes.watchlist.Fundamental") as MockFundamental:
        instance = MockFundamental.return_value
        instance.get_company_info.return_value = {"company_name": "Apple Inc."}
        instance.get_current_price.return_value = 150.0

        client.post("/api/v1/watchlists/ta_cac_1/add", json={"ticker": "AAPL"})
        response = client.post(
            "/api/v1/watchlists/ta_cac_1/add", json={"ticker": "AAPL"}
        )
    assert response.status_code == 200
    assert response.json()["success"] is False


def test_remove_ticker(make_client, isolated_cresus_home):
    _write_watchlist(
        isolated_cresus_home, "ta_cac_1", [{"ticker": "AAPL"}, {"ticker": "MSFT"}]
    )

    client = make_client(router)
    response = client.delete("/api/v1/watchlists/ta_cac_1/AAPL")
    assert response.status_code == 200

    tickers_resp = client.get("/api/v1/watchlists/ta_cac_1/tickers")
    assert tickers_resp.json()["tickers"] == ["MSFT"]


def test_remove_last_ticker_deletes_file(make_client, isolated_cresus_home):
    _write_watchlist(isolated_cresus_home, "ta_cac_1", [{"ticker": "AAPL"}])

    client = make_client(router)
    response = client.delete("/api/v1/watchlists/ta_cac_1/AAPL")
    assert response.status_code == 200

    assert not _watchlist_path(isolated_cresus_home, "ta_cac_1").exists()


def test_remove_ticker_missing_watchlist_404(make_client, isolated_cresus_home):
    client = make_client(router)
    response = client.delete("/api/v1/watchlists/no_such_strategy/AAPL")
    assert response.status_code == 404


def test_remove_ticker_not_in_watchlist_404(make_client, isolated_cresus_home):
    _write_watchlist(isolated_cresus_home, "ta_cac_1", [{"ticker": "AAPL"}])

    client = make_client(router)
    response = client.delete("/api/v1/watchlists/ta_cac_1/GOOG")
    assert response.status_code == 404


def test_historical_ticker_not_in_watchlist_404(make_client, isolated_cresus_home):
    _write_watchlist(isolated_cresus_home, "ta_cac_1", [{"ticker": "AAPL"}])

    client = make_client(router)
    response = client.get("/api/v1/watchlists/ta_cac_1/historical/MSFT")
    assert response.status_code == 404


def test_historical_missing_watchlist_404(make_client, isolated_cresus_home):
    client = make_client(router)
    response = client.get("/api/v1/watchlists/no_such_strategy/historical/AAPL")
    assert response.status_code == 404


def test_historical_success(make_client, isolated_cresus_home):
    _write_watchlist(isolated_cresus_home, "ta_cac_1", [{"ticker": "AAPL"}])

    dates = pd.date_range("2025-01-01", periods=60, freq="D")
    df = pd.DataFrame(
        {
            "timestamp": dates,
            "open": [100.0] * 60,
            "high": [101.0] * 60,
            "low": [99.0] * 60,
            "close": [100.5] * 60,
            "volume": [1000] * 60,
        }
    )

    client = make_client(router)
    # DataHistory is imported locally inside get_ticker_historical(), so it
    # must be patched at its source (tools.data), not on the route module.
    with patch("tools.data.DataHistory") as MockHistory:
        MockHistory.return_value.load_all.return_value = df
        response = client.get(
            "/api/v1/watchlists/ta_cac_1/historical/AAPL?period=1M"
        )
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["count"] == 30
    assert "ema_20" in data["data"][0]

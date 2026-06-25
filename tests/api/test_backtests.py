"""Tests for /backtests endpoints.

BacktestManager() resolves backtests under {CRESUS_HOME}/.cresus/db/backtests,
isolated per test by the autouse isolated_cresus_home fixture. POST /backtests
fires a real BacktestAgent or MarketPrepAgent in a background daemon thread -
both are mocked at their actual import sites (agents.backtest.agent and
agents.market_prep.agent respectively; the route imports the latter locally
inside the closure, not at module level) so tests stay fast and never touch
real market data.
"""

from unittest.mock import patch

from api.routes.backtests import router
from tools.backtest.manager import BacktestManager


def _make_finished_backtest(strategy="strat_a", backtest_id="20260101_120000_aaaaaaaa", **metric_overrides):
    manager = BacktestManager()
    manager.create_backtest_dir(strategy, backtest_id)
    metrics = {
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
        "total_return_pct": 12.5,
        "max_drawdown_pct": 4.0,
        "sharpe_ratio": 1.8,
        "total_trades": 6,
        "win_rate_pct": 66.6,
        "start_value": 10000.0,
    }
    metrics.update(metric_overrides)
    manager.save_metrics(strategy, backtest_id, metrics)
    return strategy, backtest_id


def test_list_backtests_empty(make_client):
    client = make_client(router)
    response = client.get("/api/v1/backtests")
    assert response.status_code == 200
    data = response.json()
    assert data["backtests"] == []
    assert data["total"] == 0


def test_list_backtests_after_create(make_client):
    client = make_client(router)
    _make_finished_backtest()

    response = client.get("/api/v1/backtests")
    data = response.json()
    assert data["total"] == 1
    assert data["backtests"][0]["strategy_name"] == "strat_a"


def test_list_backtests_filtered_by_strategy(make_client):
    client = make_client(router)
    _make_finished_backtest(strategy="strat_a", backtest_id="20260101_120000_aaaaaaaa")
    _make_finished_backtest(strategy="strat_b", backtest_id="20260101_120000_bbbbbbbb")

    response = client.get("/api/v1/backtests?strategy=strat_b")
    data = response.json()
    assert data["total"] == 1
    assert data["backtests"][0]["strategy_name"] == "strat_b"


def test_run_backtest_missing_strategy_400(make_client):
    client = make_client(router)
    response = client.post("/api/v1/backtests", json={})
    assert response.status_code == 400


def test_run_historical_backtest_starts_and_returns_id(make_client):
    client = make_client(router)

    with patch("api.routes.backtests._get_backtest_agent") as mock_get_agent:
        mock_get_agent.return_value.process.return_value = {"status": "success"}
        response = client.post(
            "/api/v1/backtests",
            json={
                "strategy": "strat_a",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["backtest_id"]
    assert data["strategy"] == "strat_a"


def test_run_live_mode_without_dates(make_client):
    client = make_client(router)

    with patch("agents.market_prep.agent.MarketPrepAgent") as MockAgent:
        MockAgent.return_value.process.return_value = {"status": "success"}
        response = client.post("/api/v1/backtests", json={"strategy": "strat_a"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["strategy_name"] == "strat_a"
    assert "watchlist_path" in data


def test_compare_backtests(make_client):
    client = make_client(router)
    _make_finished_backtest(strategy="strat_a", backtest_id="20260101_120000_aaaaaaaa")
    _make_finished_backtest(strategy="strat_b", backtest_id="20260101_120000_bbbbbbbb")

    response = client.get(
        "/api/v1/backtests/compare",
        params={"items": "strat_a:20260101_120000_aaaaaaaa,strat_b:20260101_120000_bbbbbbbb"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2


def test_compare_backtests_invalid_format_400(make_client):
    client = make_client(router)
    response = client.get("/api/v1/backtests/compare", params={"items": "not-valid"})
    assert response.status_code == 400


def test_get_backtest_metrics(make_client):
    client = make_client(router)
    strategy, backtest_id = _make_finished_backtest()

    response = client.get(f"/api/v1/backtests/{strategy}/{backtest_id}/metrics")
    assert response.status_code == 200
    assert response.json()["metrics"]["total_return_pct"] == 12.5


def test_get_backtest_metrics_missing_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/backtests/ghost/ghost/metrics")
    assert response.status_code == 404


def test_get_backtest_history_in_progress_empty(make_client):
    client = make_client(router)
    strategy, backtest_id = _make_finished_backtest()

    response = client.get(f"/api/v1/backtests/{strategy}/{backtest_id}/history")
    assert response.status_code == 200
    assert response.json()["history"] == []


def test_get_backtest_history_missing_backtest_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/backtests/ghost/ghost/history")
    assert response.status_code == 404


def test_get_backtest_distribution_in_progress(make_client):
    client = make_client(router)
    strategy, backtest_id = _make_finished_backtest()

    response = client.get(f"/api/v1/backtests/{strategy}/{backtest_id}/distribution")
    assert response.status_code == 200
    assert response.json()["data"]["distribution"] == []


def test_get_backtest_distribution_missing_backtest_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/backtests/ghost/ghost/distribution")
    assert response.status_code == 404


def test_get_backtest_full(make_client):
    client = make_client(router)
    strategy, backtest_id = _make_finished_backtest()

    response = client.get(f"/api/v1/backtests/{strategy}/{backtest_id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["backtest_id"] == backtest_id
    assert data["portfolio_metrics"]["total_return_pct"] == 12.5


def test_get_backtest_missing_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/backtests/ghost/ghost")
    assert response.status_code == 404


def test_delete_backtest(make_client):
    client = make_client(router)
    strategy, backtest_id = _make_finished_backtest()

    response = client.delete(f"/api/v1/backtests/{strategy}/{backtest_id}")
    assert response.status_code == 200
    assert client.get(f"/api/v1/backtests/{strategy}/{backtest_id}").status_code == 404


def test_delete_backtest_missing_400(make_client):
    client = make_client(router)
    response = client.delete("/api/v1/backtests/ghost/ghost")
    assert response.status_code == 400


def test_get_strategy_watchlist_no_file(make_client):
    client = make_client(router)
    response = client.get("/api/v1/backtests/strategy/strat_a/watchlist")
    assert response.status_code == 200
    assert response.json()["data"]["watchlist"] == []


def test_get_backtest_watchlist_missing_backtest_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/backtests/ghost/ghost/watchlist")
    assert response.status_code == 404


def test_get_backtest_watchlist_no_file(make_client):
    client = make_client(router)
    strategy, backtest_id = _make_finished_backtest()

    response = client.get(f"/api/v1/backtests/{strategy}/{backtest_id}/watchlist")
    assert response.status_code == 200
    assert response.json()["data"]["watchlist"] == []


def test_get_backtest_watchlist_with_data(make_client, isolated_cresus_home):
    import pandas as pd

    client = make_client(router)
    strategy, backtest_id = _make_finished_backtest()

    watchlist_dir = (
        isolated_cresus_home / ".cresus" / "db" / "backtests" / strategy / backtest_id / "watchlist"
    )
    pd.DataFrame([{"ticker": "AAPL", "score": 0.9}]).to_csv(
        watchlist_dir / f"{strategy}.csv", index=False
    )

    response = client.get(f"/api/v1/backtests/{strategy}/{backtest_id}/watchlist")
    assert response.status_code == 200
    assert response.json()["data"]["watchlist"][0]["ticker"] == "AAPL"


def test_regenerate_backtest_watchlist_missing_backtest_404(make_client):
    client = make_client(router)
    response = client.post("/api/v1/backtests/ghost/ghost/watchlist/regenerate")
    assert response.status_code == 404


def test_regenerate_backtest_watchlist_no_file(make_client):
    client = make_client(router)
    strategy, backtest_id = _make_finished_backtest()

    response = client.post(f"/api/v1/backtests/{strategy}/{backtest_id}/watchlist/regenerate")
    assert response.status_code == 200
    assert response.json()["data"]["watchlist"] == []

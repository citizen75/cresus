"""Tests for /bots endpoints.

api.routes.bots caches its BotManager/PortfolioManager via @lru_cache(maxsize=1)
at module level - those caches must be cleared per test, otherwise the first
test's instance (bound to that test's isolated home) leaks into every test
that runs after it.
"""

import pandas as pd
import pytest

from api.routes import bots as bots_module
from api.routes.bots import router


@pytest.fixture(autouse=True)
def _clear_bot_manager_caches():
    bots_module._get_bot_manager.cache_clear()
    bots_module._get_portfolio_manager.cache_clear()
    yield
    bots_module._get_bot_manager.cache_clear()
    bots_module._get_portfolio_manager.cache_clear()


@pytest.fixture
def strategy_name(isolated_cresus_home):
    """Create a minimal real strategy on disk so create_bot() can copy it."""
    from tools.strategy import StrategyManager

    StrategyManager().save_strategy(
        "ta_for_bot",
        {"name": "ta_for_bot", "engine": "TaModel", "universe": "cac40"},
    )
    return "ta_for_bot"


def _create_bot(client, name="bot_test_1", strategy="ta_for_bot"):
    return client.post("/api/v1/bots", json={"name": name, "strategy": strategy})


def test_list_bots_empty(make_client):
    client = make_client(router)
    response = client.get("/api/v1/bots")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["bots"] == []
    assert data["total"] == 0


def test_create_bot(make_client, strategy_name):
    client = make_client(router)
    response = _create_bot(client)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["bot"]["name"] == "bot_test_1"
    assert data["bot"]["state"] == "inactive"


def test_create_bot_unknown_strategy_400(make_client, isolated_cresus_home):
    client = make_client(router)
    response = _create_bot(client, strategy="does_not_exist")
    assert response.status_code == 400


def test_create_duplicate_bot_400(make_client, strategy_name):
    client = make_client(router)
    _create_bot(client)
    response = _create_bot(client)
    assert response.status_code == 400


def test_get_bot_info(make_client, strategy_name):
    client = make_client(router)
    _create_bot(client)

    response = client.get("/api/v1/bots/bot_test_1")
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["name"] == "bot_test_1"
    assert data["bot_dir"].endswith("bot_test_1")


def test_get_missing_bot_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/bots/ghost")
    assert response.status_code == 404


def test_bots_summary(make_client, strategy_name):
    client = make_client(router)
    _create_bot(client)

    response = client.get("/api/v1/bots/summary")
    assert response.status_code == 200


def test_list_bots_after_create(make_client, strategy_name):
    client = make_client(router)
    _create_bot(client, name="bot_a")
    _create_bot(client, name="bot_b")

    response = client.get("/api/v1/bots")
    data = response.json()
    assert data["total"] == 2
    names = {b["name"] for b in data["bots"]}
    assert names == {"bot_a", "bot_b"}


def test_activate_and_deactivate_bot(make_client, strategy_name):
    client = make_client(router)
    _create_bot(client)

    response = client.post("/api/v1/bots/bot_test_1/activate")
    assert response.status_code == 200
    assert client.get("/api/v1/bots/bot_test_1").json()["config"]["state"] == "active"

    response = client.post("/api/v1/bots/bot_test_1/deactivate")
    assert response.status_code == 200
    assert client.get("/api/v1/bots/bot_test_1").json()["config"]["state"] == "inactive"


def test_activate_missing_bot_404(make_client):
    client = make_client(router)
    assert client.post("/api/v1/bots/ghost/activate").status_code == 404


def test_deactivate_missing_bot_404(make_client):
    client = make_client(router)
    assert client.post("/api/v1/bots/ghost/deactivate").status_code == 404


def test_delete_bot(make_client, strategy_name):
    client = make_client(router)
    _create_bot(client)

    response = client.delete("/api/v1/bots/bot_test_1")
    assert response.status_code == 200
    assert client.get("/api/v1/bots/bot_test_1").status_code == 404


def test_delete_missing_bot_404(make_client):
    client = make_client(router)
    assert client.delete("/api/v1/bots/ghost").status_code == 404


def test_run_missing_bot_404(make_client):
    client = make_client(router)
    response = client.post("/api/v1/bots/ghost/run")
    assert response.status_code == 404


def test_run_bot_success(make_client, strategy_name, monkeypatch):
    """Mock BotFinance entirely - exercising the real trading pipeline needs
    live market data and is out of scope for a fast API contract test."""
    client = make_client(router)
    _create_bot(client)

    class StubBotFinance:
        def __init__(self, name, bot_dir):
            self.name = name
            self.bot_dir = bot_dir

        def activate(self):
            pass

        def run(self, params=None):
            return {"status": "success", "step": params.get("step"), "name": self.name}

    monkeypatch.setattr("bot.finance.BotFinance", StubBotFinance)

    response = client.post("/api/v1/bots/bot_test_1/run")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["step"] == "pre_market"


def test_run_bot_failure_returns_500(make_client, strategy_name, monkeypatch):
    client = make_client(router)
    _create_bot(client)

    class StubBotFinance:
        def __init__(self, name, bot_dir):
            pass

        def activate(self):
            pass

        def run(self, params=None):
            return {"status": "error", "message": "no data"}

    monkeypatch.setattr("bot.finance.BotFinance", StubBotFinance)

    response = client.post("/api/v1/bots/bot_test_1/run")
    assert response.status_code == 500


def test_get_bot_watchlist_empty(make_client, strategy_name):
    client = make_client(router)
    _create_bot(client)

    response = client.get("/api/v1/bots/bot_test_1/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert data["watchlist"] == []
    assert data["total"] == 0


def test_get_bot_watchlist_with_data(make_client, strategy_name):
    from tools.bot import BotManager

    client = make_client(router)
    _create_bot(client)

    bot_dir = BotManager().get_bot_dir("bot_test_1")
    pd.DataFrame(
        [
            {"ticker": "AAPL", "signal_score": 0.9},
            {"ticker": "MSFT", "signal_score": 0.5},
        ]
    ).to_csv(bot_dir / "watchlist.csv", index=False)

    response = client.get("/api/v1/bots/bot_test_1/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    tickers = {row["ticker"] for row in data["watchlist"]}
    assert tickers == {"AAPL", "MSFT"}


def test_get_bot_watchlist_with_limit(make_client, strategy_name):
    from tools.bot import BotManager

    client = make_client(router)
    _create_bot(client)

    bot_dir = BotManager().get_bot_dir("bot_test_1")
    pd.DataFrame(
        [{"ticker": t, "signal_score": i} for i, t in enumerate(["A", "B", "C"])]
    ).to_csv(bot_dir / "watchlist.csv", index=False)

    response = client.get("/api/v1/bots/bot_test_1/watchlist?limit=1")
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_get_bot_watchlist_missing_bot_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/bots/ghost/watchlist")
    assert response.status_code == 404


def test_get_bot_orders_empty(make_client, strategy_name):
    client = make_client(router)
    _create_bot(client)

    response = client.get("/api/v1/bots/bot_test_1/orders")
    assert response.status_code == 200


def test_get_bot_orders_missing_bot_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/bots/ghost/orders")
    assert response.status_code == 404


def test_delete_bot_order_missing_bot_404(make_client):
    client = make_client(router)
    response = client.delete("/api/v1/bots/ghost/orders/some-id")
    assert response.status_code == 404


def test_get_bot_positions_empty(make_client, strategy_name):
    client = make_client(router)
    _create_bot(client)

    response = client.get("/api/v1/bots/bot_test_1/positions")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "bot_test_1"
    assert data["positions"] == []
    assert data["total_value"] == 0


def test_get_bot_positions_missing_bot_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/bots/ghost/positions")
    assert response.status_code == 404

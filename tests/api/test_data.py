"""Tests for /data endpoints.

Universe/blacklist storage resolves under {CRESUS_HOME}/.cresus/db/universes,
isolated per test by the autouse isolated_cresus_home fixture - real Universe
CRUD is exercised directly (filesystem-only, no network). Anything that would
otherwise call out to yfinance or financedatabase (TickerIntelligence,
Fundamental, DataHistory, get_equities/get_etfs/...) is mocked per the
src/api/CLAUDE.local.md "never use yfinance or financedatabase" rule.

While writing these tests, discovered that nearly every error path in
src/api/routes/data.py did `return {"error": ...}, 404` - FastAPI does not
treat a returned (body, status_code) tuple specially, so every one of these
silently responded 200 with a `[body, code]` JSON array instead of the
intended error status. Fixed in source by raising HTTPException instead.
"""

from unittest.mock import patch

from api.routes.data import router
from tools.universe.universe import Universe


def _make_universe(name="cac40", tickers=("AAPL", "MSFT")):
    uni = Universe(name)
    uni.create(list(tickers))
    return uni


def test_get_categories(make_client):
    client = make_client(router)
    response = client.get("/api/v1/data/categories")
    assert response.status_code == 200
    ids = {c["id"] for c in response.json()["categories"]}
    assert "stocks" in ids


def test_list_all_universes_empty(make_client):
    client = make_client(router)
    response = client.get("/api/v1/data/universes/list")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_list_all_universes_with_data(make_client):
    _make_universe("cac40")
    client = make_client(router)

    response = client.get("/api/v1/data/universes/list?use_cache=false")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["universes"][0]["id"] == "cac40"
    assert data["universes"][0]["count"] == 2


def test_get_universes_for_category_empty(make_client):
    client = make_client(router)
    response = client.get("/api/v1/data/universes?category=stocks")
    assert response.status_code == 200
    assert response.json()["universes"] == []


def test_get_universes_for_category_with_data(make_client):
    _make_universe("cac40")
    client = make_client(router)
    response = client.get("/api/v1/data/universes?category=stocks")
    assert response.status_code == 200
    universes = response.json()["universes"]
    assert any(u["id"] == "cac40" for u in universes)


def test_get_tickers_missing_universe_404(make_client):
    client = make_client(router)
    response = client.get(
        "/api/v1/data/tickers?category=stocks&universe=ghost&enrich=false"
    )
    assert response.status_code == 404


def test_get_tickers_success_no_enrich(make_client):
    _make_universe("cac40", tickers=("AAPL", "MSFT"))
    client = make_client(router)

    response = client.get(
        "/api/v1/data/tickers?category=stocks&universe=cac40&enrich=false"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    symbols = {t["symbol"] for t in data["tickers"]}
    assert symbols == {"AAPL", "MSFT"}


def test_search_tickers_empty(make_client):
    client = make_client(router)
    response = client.get("/api/v1/data/search?q=AAPL")
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_get_universe_tickers_missing_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/data/universe/ghost?enrich=false")
    assert response.status_code == 404


def test_get_universe_tickers_success(make_client):
    _make_universe("cac40", tickers=("AAPL",))
    client = make_client(router)
    response = client.get("/api/v1/data/universe/cac40?enrich=false")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["tickers"][0]["symbol"] == "AAPL"


def test_get_universe_info_missing_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/data/universe/ghost/info")
    assert response.status_code == 404


def test_get_universe_info_success(make_client):
    _make_universe("cac40", tickers=("AAPL",))
    client = make_client(router)
    response = client.get("/api/v1/data/universe/cac40/info")
    assert response.status_code == 200
    assert response.json()["info"]["count"] == 1


def test_create_universe_without_id_400(make_client):
    client = make_client(router)
    response = client.post("/api/v1/data/universe", json={"tickers": ["AAPL"]})
    assert response.status_code == 400


def test_create_universe_with_id(make_client):
    client = make_client(router)
    response = client.post(
        "/api/v1/data/universe/my_universe", json={"tickers": ["AAPL", "MSFT"]}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "created"
    assert Universe("my_universe").exists()


def test_create_universe_with_id_duplicate_409(make_client):
    _make_universe("cac40")
    client = make_client(router)
    response = client.post("/api/v1/data/universe/cac40", json={"tickers": ["AAPL"]})
    assert response.status_code == 409


def test_update_universe(make_client):
    _make_universe("cac40", tickers=("AAPL",))
    client = make_client(router)
    response = client.put(
        "/api/v1/data/universe/cac40", json={"tickers": ["MSFT", "GOOGL"]}
    )
    assert response.status_code == 200
    assert Universe("cac40").get_tickers() == ["MSFT", "GOOGL"]


def test_update_universe_missing_404(make_client):
    client = make_client(router)
    response = client.put("/api/v1/data/universe/ghost", json={"tickers": ["AAPL"]})
    assert response.status_code == 404


def test_delete_universe(make_client):
    _make_universe("cac40")
    client = make_client(router)
    response = client.delete("/api/v1/data/universe/cac40")
    assert response.status_code == 200
    assert not Universe("cac40").exists()


def test_delete_universe_missing_404(make_client):
    client = make_client(router)
    response = client.delete("/api/v1/data/universe/ghost")
    assert response.status_code == 404


def test_rename_universe(make_client):
    _make_universe("cac40", tickers=("AAPL",))
    client = make_client(router)
    response = client.patch("/api/v1/data/universe/cac40", json={"new_id": "cac_renamed"})
    assert response.status_code == 200
    assert not Universe("cac40").exists()
    assert Universe("cac_renamed").exists()


def test_rename_universe_missing_404(make_client):
    client = make_client(router)
    response = client.patch("/api/v1/data/universe/ghost", json={"new_id": "x"})
    assert response.status_code == 404


def test_rename_universe_target_exists_409(make_client):
    _make_universe("cac40")
    _make_universe("nasdaq_100")
    client = make_client(router)
    response = client.patch(
        "/api/v1/data/universe/cac40", json={"new_id": "nasdaq_100"}
    )
    assert response.status_code == 409


def test_add_tickers_to_universe(make_client):
    _make_universe("cac40", tickers=("AAPL",))
    client = make_client(router)
    response = client.post(
        "/api/v1/data/universe/cac40/tickers", json={"tickers": ["MSFT"]}
    )
    assert response.status_code == 200
    assert set(Universe("cac40").get_tickers()) == {"AAPL", "MSFT"}


def test_add_tickers_missing_universe_404(make_client):
    client = make_client(router)
    response = client.post(
        "/api/v1/data/universe/ghost/tickers", json={"tickers": ["AAPL"]}
    )
    assert response.status_code == 404


def test_remove_tickers_from_universe(make_client):
    _make_universe("cac40", tickers=("AAPL", "MSFT"))
    client = make_client(router)
    response = client.request(
        "DELETE", "/api/v1/data/universe/cac40/tickers", json={"tickers": ["MSFT"]}
    )
    assert response.status_code == 200
    assert Universe("cac40").get_tickers() == ["AAPL"]


def test_remove_tickers_missing_universe_404(make_client):
    client = make_client(router)
    response = client.request(
        "DELETE", "/api/v1/data/universe/ghost/tickers", json={"tickers": ["AAPL"]}
    )
    assert response.status_code == 404


def test_filter_tickers_invalid_asset_type(make_client):
    client = make_client(router)
    response = client.get("/api/v1/data/filter?asset_type=bogus")
    assert response.status_code == 200
    assert response.json()["error"]


def test_filter_tickers_mocked_success(make_client):
    import pandas as pd

    client = make_client(router)
    fake_df = pd.DataFrame(
        {"name": ["Apple Inc."], "currency": ["USD"], "exchange": ["NASDAQ"], "country": ["United States"], "sector": ["Tech"], "industry": ["Hardware"]},
        index=["AAPL"],
    )
    with patch("api.routes.data.get_equities") as mock_get_equities:
        mock_get_equities.return_value.select.return_value = fake_df
        response = client.get(
            "/api/v1/data/filter?asset_type=stocks&countries=US&enrich=false"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["tickers"][0]["symbol"] == "AAPL"


def test_get_category_tickers_no_enrich(make_client):
    _make_universe("cac40", tickers=("AAPL",))
    client = make_client(router)
    response = client.get("/api/v1/data/category/stocks?enrich=false")
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_get_category_tickers_unknown_category(make_client):
    client = make_client(router)
    response = client.get("/api/v1/data/category/bogus?enrich=false")
    assert response.status_code == 200
    assert response.json()["tickers"] == []


def test_get_enriched_ticker(make_client):
    client = make_client(router)
    with patch("api.routes.data.TickerIntelligence") as MockTI:
        MockTI.return_value.get_enriched_data.return_value = {"symbol": "AAPL", "price": 150.0}
        response = client.get("/api/v1/data/ticker/AAPL/enriched")

    assert response.status_code == 200
    assert response.json()["symbol"] == "AAPL"


def test_get_ticker_summary(make_client):
    client = make_client(router)
    with patch("api.routes.data.TickerIntelligence") as MockTI:
        MockTI.return_value.get_summary.return_value = {"symbol": "AAPL", "pe_ratio": 30.0}
        response = client.get("/api/v1/data/ticker/AAPL/summary")

    assert response.status_code == 200
    assert response.json()["pe_ratio"] == 30.0


def test_batch_enrich_tickers(make_client):
    client = make_client(router)
    with patch("api.routes.data.TickerIntelligence") as MockTI:
        MockTI.batch_enrich.return_value = {"AAPL": {"price": 150.0}}
        response = client.post(
            "/api/v1/data/tickers/enrich", json={"tickers": ["AAPL"]}
        )

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_get_all_tickers_empty(make_client):
    client = make_client(router)
    response = client.get("/api/v1/data/tickers/all")
    assert response.status_code == 200
    assert response.json()["tickers"] == []


def test_get_all_tickers_with_universe(make_client):
    _make_universe("cac40", tickers=("AAPL",))
    client = make_client(router)
    response = client.get("/api/v1/data/tickers/all")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1


def test_get_ticker_info_not_found_404(make_client):
    client = make_client(router)
    with patch("api.routes.data.manager") as mock_manager:
        mock_manager.get_ticker_info.return_value = None
        response = client.get("/api/v1/data/tickers/GHOST")
    assert response.status_code == 404


def test_get_ticker_info_success(make_client):
    client = make_client(router)
    with patch("api.routes.data.manager") as mock_manager:
        mock_manager.get_ticker_info.return_value = {"symbol": "AAPL", "name": "Apple"}
        response = client.get("/api/v1/data/tickers/AAPL")
    assert response.status_code == 200
    assert response.json()["info"]["name"] == "Apple"


def test_get_ticker_history_no_cached_data(make_client):
    client = make_client(router)
    with patch("tools.data.core.DataHistory") as MockHistory:
        import pandas as pd

        MockHistory.return_value.load_all.return_value = pd.DataFrame()
        MockHistory.return_value.fetch.return_value = {"status": "error"}
        response = client.get("/api/v1/data/history/AAPL")

    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["history"] == []


def test_clear_cache_all(make_client):
    client = make_client(router)
    response = client.post("/api/v1/data/cache/clear")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_clear_cache_specific_ticker_not_cached(make_client):
    client = make_client(router)
    response = client.post("/api/v1/data/cache/clear?ticker=AAPL")
    assert response.status_code == 200
    assert response.json()["status"] == "not_found"


def test_get_ticker_fundamental_cached(make_client):
    client = make_client(router)
    with patch("tools.data.core.Fundamental") as MockFundamental:
        MockFundamental.return_value.load.return_value = {"symbol": "AAPL", "data": {}}
        response = client.get("/api/v1/data/fundamental/AAPL")

    assert response.status_code == 200
    assert response.json()["symbol"] == "AAPL"


def test_get_ticker_fundamental_fetches_when_not_cached(make_client):
    client = make_client(router)
    with patch("tools.data.core.Fundamental") as MockFundamental:
        MockFundamental.return_value.load.return_value = None
        MockFundamental.return_value.fetch.return_value = {"symbol": "AAPL", "fetched": True}
        response = client.get("/api/v1/data/fundamental/AAPL")

    assert response.status_code == 200
    assert response.json()["fetched"] is True

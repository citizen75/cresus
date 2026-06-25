"""Tests for /screener endpoints.

ScreenerManager() resolves to {CRESUS_HOME}/.cresus/db/screeners, isolated
per test by the autouse isolated_cresus_home fixture. /run and /builder both
hand off to a real ScreenerAgent that screens live market data in a thread
pool - mocked here so these tests stay fast and offline; the DSL/screening
logic itself already has direct coverage in tests/test_screener.py.
"""

from unittest.mock import patch

from api.routes.screener import router, extract_indicators_from_formula


def _create_screener(client, name="scr_a", source="cac40", formula="rsi_14[0] > 50"):
    return client.post(
        "/api/v1/screener/screeners",
        json={"name": name, "source": source, "formula": formula},
    )


def test_extract_indicators_from_formula():
    indicators = extract_indicators_from_formula("sha_10_green[0] and rsi_14 > 50")
    assert "rsi_14" in indicators
    assert "sha_10_green" in indicators
    assert "and" not in indicators


def test_list_screeners_empty(make_client):
    client = make_client(router)
    response = client.get("/api/v1/screener/screeners")
    assert response.status_code == 200
    data = response.json()
    assert data["screeners"] == []
    assert data["total"] == 0


def test_create_and_get_screener(make_client):
    client = make_client(router)
    response = _create_screener(client)
    assert response.status_code == 200

    get_resp = client.get("/api/v1/screener/screeners/scr_a")
    assert get_resp.status_code == 200
    screener = get_resp.json()["screener"]
    assert screener["name"] == "scr_a"
    assert screener["source"] == "cac40"
    # indicators auto-extracted from formula since none were provided
    assert "rsi_14" in screener["indicators"]


def test_create_screener_via_query_params(make_client):
    client = make_client(router)
    response = client.post(
        "/api/v1/screener/screeners",
        params={"name": "scr_q", "source": "nasdaq_100", "formula": "ema_20[0] > close[0]"},
    )
    assert response.status_code == 200
    screener = client.get("/api/v1/screener/screeners/scr_q").json()["screener"]
    assert screener["source"] == "nasdaq_100"


def test_create_screener_missing_name_400(make_client):
    client = make_client(router)
    response = client.post("/api/v1/screener/screeners", json={"source": "cac40"})
    assert response.status_code == 400


def test_create_duplicate_screener_400(make_client):
    client = make_client(router)
    _create_screener(client)
    response = _create_screener(client)
    assert response.status_code == 400


def test_get_missing_screener_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/screener/screeners/ghost")
    assert response.status_code == 404


def test_list_screeners_after_create(make_client):
    client = make_client(router)
    _create_screener(client, name="scr_1")
    _create_screener(client, name="scr_2")

    response = client.get("/api/v1/screener/screeners")
    data = response.json()
    assert data["total"] == 2
    names = {s["name"] for s in data["screeners"]}
    assert names == {"scr_1", "scr_2"}


def test_update_screener(make_client):
    client = make_client(router)
    _create_screener(client)

    response = client.put(
        "/api/v1/screener/screeners/scr_a",
        json={"formula": "adx_14[0] > 25", "description": "trend filter"},
    )
    assert response.status_code == 200

    screener = client.get("/api/v1/screener/screeners/scr_a").json()["screener"]
    assert screener["formula"] == "adx_14[0] > 25"
    assert screener["description"] == "trend filter"
    assert "adx_14" in screener["indicators"]


def test_update_missing_screener_404(make_client):
    client = make_client(router)
    response = client.put("/api/v1/screener/screeners/ghost", json={"formula": "x"})
    assert response.status_code == 404


def test_delete_screener(make_client):
    client = make_client(router)
    _create_screener(client)

    response = client.delete("/api/v1/screener/screeners/scr_a")
    assert response.status_code == 200
    assert client.get("/api/v1/screener/screeners/scr_a").status_code == 404


def test_delete_missing_screener_400(make_client):
    client = make_client(router)
    response = client.delete("/api/v1/screener/screeners/ghost")
    assert response.status_code == 400


def test_run_missing_screener_404(make_client):
    client = make_client(router)
    response = client.post("/api/v1/screener/screeners/ghost/run")
    assert response.status_code == 404


def test_run_screener_success(make_client):
    client = make_client(router)
    _create_screener(client)

    with patch("api.routes.screener.ScreenerAgent") as MockAgent:
        MockAgent.return_value.process.return_value = {
            "status": "success",
            "matches": [{"ticker": "AAPL", "rsi_14": 65.0}],
            "tickers_processed": 40,
            "tickers_skipped": 0,
            "match_count": 1,
            "message": "Screening complete",
        }
        response = client.post("/api/v1/screener/screeners/scr_a/run")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["match_count"] == 1
    assert data["result_id"] is not None

    results_resp = client.get("/api/v1/screener/screeners/scr_a/results")
    assert results_resp.json()["total"] == 1


def test_run_screener_failure_not_saved(make_client):
    client = make_client(router)
    _create_screener(client)

    with patch("api.routes.screener.ScreenerAgent") as MockAgent:
        MockAgent.return_value.process.return_value = {
            "status": "error",
            "message": "no data available",
        }
        response = client.post("/api/v1/screener/screeners/scr_a/run")

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert client.get("/api/v1/screener/screeners/scr_a/results").json()["total"] == 0


def test_get_screener_result_and_delete(make_client):
    client = make_client(router)
    _create_screener(client)

    with patch("api.routes.screener.ScreenerAgent") as MockAgent:
        MockAgent.return_value.process.return_value = {
            "status": "success",
            "matches": [{"ticker": "AAPL"}],
            "match_count": 1,
        }
        run_resp = client.post("/api/v1/screener/screeners/scr_a/run")

    result_id = run_resp.json()["result_id"]

    get_resp = client.get(f"/api/v1/screener/screeners/scr_a/results/{result_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"] == [{"ticker": "AAPL"}]

    del_resp = client.delete(f"/api/v1/screener/screeners/scr_a/results/{result_id}")
    assert del_resp.status_code == 200
    assert client.get(f"/api/v1/screener/screeners/scr_a/results/{result_id}").status_code == 404


def test_get_missing_result_404(make_client):
    client = make_client(router)
    _create_screener(client)
    response = client.get("/api/v1/screener/screeners/scr_a/results/does-not-exist")
    assert response.status_code == 404


def test_clear_screener_results(make_client):
    client = make_client(router)
    _create_screener(client)

    with patch("api.routes.screener.ScreenerAgent") as MockAgent:
        MockAgent.return_value.process.return_value = {
            "status": "success",
            "matches": [{"ticker": "AAPL"}],
            "match_count": 1,
        }
        client.post("/api/v1/screener/screeners/scr_a/run")

    response = client.post("/api/v1/screener/screeners/scr_a/results/clear")
    assert response.status_code == 200
    assert client.get("/api/v1/screener/screeners/scr_a/results").json()["total"] == 0


def test_builder_requires_formula(make_client):
    client = make_client(router)
    response = client.post("/api/v1/screener/builder", json={"source": "cac40"})
    assert response.status_code == 400


def test_builder_requires_source_or_tickers(make_client):
    client = make_client(router)
    response = client.post(
        "/api/v1/screener/builder", json={"formula": "rsi_14[0] > 50"}
    )
    assert response.status_code == 400


def test_builder_success(make_client):
    client = make_client(router)
    with patch("api.routes.screener.ScreenerAgent") as MockAgent:
        MockAgent.return_value.process.return_value = {
            "status": "success",
            "matches": [{"ticker": "AAPL", "rsi_14": 65.0}],
            "match_count": 1,
            "tickers_processed": 10,
            "tickers_skipped": 0,
        }
        response = client.post(
            "/api/v1/screener/builder",
            json={"formula": "rsi_14[0] > 50", "source": "cac40"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["match_count"] == 1
    assert "rsi_14" in data["indicators"]


def test_builder_propagates_failure_as_400(make_client):
    client = make_client(router)
    with patch("api.routes.screener.ScreenerAgent") as MockAgent:
        MockAgent.return_value.process.return_value = {
            "status": "error",
            "message": "bad formula",
        }
        response = client.post(
            "/api/v1/screener/builder",
            json={"formula": "rsi_14[0] > 50", "source": "cac40"},
        )
    assert response.status_code == 400

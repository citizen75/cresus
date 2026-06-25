"""Tests for /alerts endpoints.

AlertManager() resolves to {CRESUS_HOME}/.cresus/db/alerts, isolated per test
by the autouse isolated_cresus_home fixture. POST /alerts/{name}/run's actual
evaluation (AlertEvaluator.evaluate_alert) screens real market data and is
mocked - this suite exercises the route's persistence/notification plumbing,
not the DSL screener itself (already covered by tests/test_screener.py and
tests/tools/test_alerts.py).
"""

from unittest.mock import MagicMock, patch

from api.routes.alerts import router
from tools.alerts.models import AlertResult


def _create_alert(client, name="alert_a", source="ticker", source_value="AAPL", formula="close[0] > 100"):
    return client.post(
        "/api/v1/alerts",
        json={"name": name, "source": source, "source_value": source_value, "formula": formula},
    )


def test_list_alerts_empty(make_client):
    client = make_client(router)
    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    data = response.json()
    assert data["alerts"] == []
    assert data["count"] == 0


def test_create_and_get_alert(make_client):
    client = make_client(router)
    response = _create_alert(client)
    assert response.status_code == 200

    get_resp = client.get("/api/v1/alerts/alert_a")
    assert get_resp.status_code == 200
    alert = get_resp.json()["alert"]
    assert alert["name"] == "alert_a"
    assert alert["source"] == "ticker"
    assert alert["formula"] == "close[0] > 100"
    assert alert["enabled"] is True


def test_create_alert_via_query_params(make_client):
    client = make_client(router)
    response = client.post(
        "/api/v1/alerts",
        params={"name": "alert_q", "source": "universe", "formula": "rsi_14[0] < 30"},
    )
    assert response.status_code == 200
    alert = client.get("/api/v1/alerts/alert_q").json()["alert"]
    assert alert["source"] == "universe"


def test_create_alert_missing_field_400(make_client):
    client = make_client(router)
    response = client.post("/api/v1/alerts", json={"name": "incomplete"})
    assert response.status_code == 400


def test_create_alert_duplicate_name_400(make_client):
    client = make_client(router)
    _create_alert(client)
    response = _create_alert(client)
    assert response.status_code == 400


def test_create_alert_invalid_source_400(make_client):
    client = make_client(router)
    response = _create_alert(client, source="not_a_real_source")
    assert response.status_code == 400


def test_get_missing_alert_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/alerts/ghost")
    assert response.status_code == 404


def test_list_alerts_after_create(make_client):
    client = make_client(router)
    _create_alert(client, name="alert_1")
    _create_alert(client, name="alert_2")

    response = client.get("/api/v1/alerts")
    data = response.json()
    assert data["count"] == 2
    names = {a["name"] for a in data["alerts"]}
    assert names == {"alert_1", "alert_2"}


def test_update_alert(make_client):
    client = make_client(router)
    _create_alert(client)

    response = client.put(
        "/api/v1/alerts/alert_a", json={"enabled": False, "formula": "close[0] > 200"}
    )
    assert response.status_code == 200

    alert = client.get("/api/v1/alerts/alert_a").json()["alert"]
    assert alert["enabled"] is False
    assert alert["formula"] == "close[0] > 200"


def test_update_alert_no_fields_400(make_client):
    client = make_client(router)
    _create_alert(client)
    response = client.put("/api/v1/alerts/alert_a", json={})
    assert response.status_code == 400


def test_update_missing_alert_400(make_client):
    client = make_client(router)
    response = client.put("/api/v1/alerts/ghost", json={"enabled": False})
    assert response.status_code == 400


def test_delete_alert(make_client):
    client = make_client(router)
    _create_alert(client)

    response = client.delete("/api/v1/alerts/alert_a")
    assert response.status_code == 200
    assert client.get("/api/v1/alerts/alert_a").status_code == 404


def test_delete_missing_alert_404(make_client):
    client = make_client(router)
    response = client.delete("/api/v1/alerts/ghost")
    assert response.status_code == 404


def test_run_missing_alert_404(make_client):
    client = make_client(router)
    response = client.post("/api/v1/alerts/ghost/run")
    assert response.status_code == 404


def test_run_alert_no_match(make_client):
    client = make_client(router)
    _create_alert(client)

    fake_result = AlertResult(
        alert_name="alert_a", matched=False, matches=[], tickers_checked=1
    )
    with patch("api.routes.alerts.AlertEvaluator") as MockEvaluator:
        MockEvaluator.return_value.evaluate_alert.return_value = fake_result
        response = client.post("/api/v1/alerts/alert_a/run")

    assert response.status_code == 200
    data = response.json()
    assert data["matched"] is False
    assert data["tickers_checked"] == 1

    # Result should have been persisted
    results_resp = client.get("/api/v1/alerts/alert_a/results")
    assert results_resp.json()["total"] == 1


def test_run_alert_with_match_sends_notification(make_client):
    client = make_client(router)
    _create_alert(client)

    fake_result = AlertResult(
        alert_name="alert_a",
        matched=True,
        matches=[{"ticker": "AAPL", "close": 150.0}],
        tickers_checked=1,
    )
    with patch("api.routes.alerts.AlertEvaluator") as MockEvaluator, patch(
        "api.routes.alerts.AlertNotifier"
    ) as MockNotifier, patch("api.routes.alerts.Fundamental") as MockFundamental:
        MockEvaluator.return_value.evaluate_alert.return_value = fake_result
        MockFundamental.return_value.get_company_info.return_value = {
            "company_name": "Apple Inc."
        }
        response = client.post("/api/v1/alerts/alert_a/run")
        assert MockNotifier.return_value.send_alert.called

    assert response.status_code == 200
    data = response.json()
    assert data["matched"] is True
    assert data["matches"][0]["company_name"] == "Apple Inc."


def test_run_alert_cleans_nan_values(make_client):
    client = make_client(router)
    _create_alert(client)

    fake_result = AlertResult(
        alert_name="alert_a",
        matched=True,
        matches=[{"ticker": "AAPL", "close": float("nan")}],
        tickers_checked=1,
    )
    with patch("api.routes.alerts.AlertEvaluator") as MockEvaluator, patch(
        "api.routes.alerts.AlertNotifier"
    ), patch("api.routes.alerts.Fundamental") as MockFundamental:
        MockEvaluator.return_value.evaluate_alert.return_value = fake_result
        MockFundamental.return_value.get_company_info.return_value = {"company_name": "Apple"}
        response = client.post("/api/v1/alerts/alert_a/run")

    assert response.status_code == 200
    assert response.json()["matches"][0]["close"] is None


def test_get_alert_results_empty(make_client):
    client = make_client(router)
    _create_alert(client)

    response = client.get("/api/v1/alerts/alert_a/results")
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_delete_alert_result(make_client):
    from datetime import datetime

    client = make_client(router)
    _create_alert(client)

    evaluated_at = datetime.now().isoformat()
    fake_result = AlertResult(
        alert_name="alert_a", matched=False, tickers_checked=0, evaluated_at=evaluated_at
    )
    with patch("api.routes.alerts.AlertEvaluator") as MockEvaluator:
        MockEvaluator.return_value.evaluate_alert.return_value = fake_result
        client.post("/api/v1/alerts/alert_a/run")

    assert client.get("/api/v1/alerts/alert_a/results").json()["total"] == 1

    # Result files are identified by a timestamp derived from evaluated_at
    # (result_id format: YYYYmmdd_HHMMSS), not by an "id" field in the JSON.
    rid = datetime.fromisoformat(evaluated_at).strftime("%Y%m%d_%H%M%S")

    response = client.delete(f"/api/v1/alerts/alert_a/results/{rid}")
    assert response.status_code == 200
    assert client.get("/api/v1/alerts/alert_a/results").json()["total"] == 0


def test_delete_missing_alert_result_404(make_client):
    client = make_client(router)
    _create_alert(client)
    response = client.delete("/api/v1/alerts/alert_a/results/does-not-exist")
    assert response.status_code == 404


def test_get_alert_logs_empty(make_client):
    client = make_client(router)
    response = client.get("/api/v1/alerts/alert_a/logs")
    assert response.status_code == 200
    assert response.json()["logs"] == []

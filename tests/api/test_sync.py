"""Tests for /sync (broker import) endpoints.

POST /sync/boursedirect talks to a real external broker (BourseDirectImporter)
and is mocked rather than exercised for real - this suite checks the route's
own request validation and error-translation logic, not the broker client.
"""

from unittest.mock import AsyncMock, patch

from api.routes.sync import router


def test_status_is_a_stub(make_client):
    client = make_client(router)
    response = client.get("/api/v1/sync/boursedirect/status?portfolio_name=demo")
    assert response.status_code == 200
    data = response.json()
    assert data == {"portfolio_name": "demo", "last_sync": None, "status": "idle"}


def test_sync_missing_fields_rejected(make_client):
    client = make_client(router)
    response = client.post("/api/v1/sync/boursedirect", json={"portfolio_name": "demo"})
    assert response.status_code == 422


def test_sync_success(make_client):
    client = make_client(router)
    with patch("api.routes.sync.BourseDirectImporter") as MockImporter:
        instance = MockImporter.return_value
        instance.sync_portfolio = AsyncMock(
            return_value={"status": "success", "portfolio_name": "demo", "positions_synced": 3}
        )
        response = client.post(
            "/api/v1/sync/boursedirect",
            json={"portfolio_name": "demo", "email": "a@b.com", "password": "secret"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    MockImporter.assert_called_once_with("a@b.com", "secret", None)


def test_sync_broker_error_returns_400(make_client):
    client = make_client(router)
    with patch("api.routes.sync.BourseDirectImporter") as MockImporter:
        instance = MockImporter.return_value
        instance.sync_portfolio = AsyncMock(
            return_value={"status": "error", "message": "Invalid credentials"}
        )
        response = client.post(
            "/api/v1/sync/boursedirect",
            json={"portfolio_name": "demo", "email": "a@b.com", "password": "wrong"},
        )
    assert response.status_code == 400
    assert "Invalid credentials" in response.json()["detail"]


def test_sync_unexpected_exception_returns_500(make_client):
    client = make_client(router)
    with patch("api.routes.sync.BourseDirectImporter", side_effect=RuntimeError("boom")):
        response = client.post(
            "/api/v1/sync/boursedirect",
            json={"portfolio_name": "demo", "email": "a@b.com", "password": "x"},
        )
    assert response.status_code == 500

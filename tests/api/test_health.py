"""Tests for /health and /config endpoints."""

from api.routes.health import router


def test_health_ok(make_client):
    client = make_client(router)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "cresus-api"}


def test_config_defaults_when_no_env_file(make_client, isolated_cresus_home):
    client = make_client(router)
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    data = response.json()
    assert data["api"]["host"] == "localhost"
    assert data["api"]["port"] == 8000


def test_config_reads_env_file(make_client, isolated_cresus_home):
    cresus_dir = isolated_cresus_home / ".cresus"
    cresus_dir.mkdir(parents=True, exist_ok=True)
    (cresus_dir / ".env").write_text(
        "# comment\nAPI_HOST=0.0.0.0\nAPI_PORT=9999\n"
    )

    client = make_client(router)
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    data = response.json()
    assert data["api"]["host"] == "0.0.0.0"
    assert data["api"]["port"] == 9999


def test_config_falls_back_on_invalid_port(make_client, isolated_cresus_home):
    cresus_dir = isolated_cresus_home / ".cresus"
    cresus_dir.mkdir(parents=True, exist_ok=True)
    (cresus_dir / ".env").write_text("API_PORT=not-a-number\n")

    client = make_client(router)
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    assert response.json()["api"]["port"] == 8000

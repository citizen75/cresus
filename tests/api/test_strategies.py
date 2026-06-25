"""Tests for /strategies endpoints. StrategyManager() with no project_root
resolves to {CRESUS_HOME}/db/strategies, redirected per-test by the autouse
isolated_cresus_home fixture.

create_strategy (POST) goes through cli.commands.strategy.StrategyCommands,
which reads the real init/templates/strategy.yml template from
CRESUS_PROJECT_ROOT (defaults to ".", i.e. wherever pytest is invoked from -
the repo root) - that part is the one piece of real repo content these tests
depend on, everything else is in the isolated tmp home.
"""

from api.routes.strategies import router


def _create(client, name="ta_test_1", universe=None):
    payload = {"name": name}
    if universe:
        payload["universe"] = universe
    return client.post("/api/v1/strategies", json=payload)


def test_list_strategies_empty(make_client):
    client = make_client(router)
    response = client.get("/api/v1/strategies")
    assert response.status_code == 200
    assert response.json() == {"strategies": []}


def test_create_and_get_strategy(make_client):
    client = make_client(router)
    create_resp = _create(client)
    assert create_resp.status_code == 200
    assert create_resp.json()["status"] == "success"

    get_resp = client.get("/api/v1/strategies/ta_test_1")
    assert get_resp.status_code == 200
    assert get_resp.json()["strategy"]["name"] == "ta_test_1"


def test_create_strategy_with_universe(make_client):
    client = make_client(router)
    _create(client, name="ta_test_universe", universe="cac40")

    response = client.get("/api/v1/strategies/ta_test_universe")
    assert response.status_code == 200
    assert response.json()["strategy"]["universe"] == "cac40"


def test_create_duplicate_name_rejected(make_client):
    client = make_client(router)
    _create(client, name="ta_dupe")
    response = _create(client, name="ta_dupe")
    assert response.status_code == 400


def test_get_missing_strategy_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/strategies/does_not_exist")
    assert response.status_code == 404


def test_list_strategies_after_create(make_client):
    client = make_client(router)
    _create(client, name="ta_list_1")
    _create(client, name="ta_list_2")

    response = client.get("/api/v1/strategies")
    assert response.status_code == 200
    names = [s["name"] for s in response.json()["strategies"]]
    assert "ta_list_1" in names
    assert "ta_list_2" in names


def test_update_strategy_partial_merge(make_client):
    client = make_client(router)
    _create(client, name="ta_update_1")

    response = client.put(
        "/api/v1/strategies/ta_update_1",
        json={"entry": {"parameters": {"foo": "bar"}}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["strategy"]["entry"]["parameters"]["foo"] == "bar"

    # Verify it persisted
    get_resp = client.get("/api/v1/strategies/ta_update_1")
    assert get_resp.json()["strategy"]["entry"]["parameters"]["foo"] == "bar"


def test_update_missing_strategy_404(make_client):
    client = make_client(router)
    response = client.put("/api/v1/strategies/does_not_exist", json={"entry": {}})
    assert response.status_code == 404


def test_duplicate_strategy_auto_name(make_client):
    client = make_client(router)
    _create(client, name="ta_orig")

    response = client.post("/api/v1/strategies/ta_orig/duplicate")
    assert response.status_code == 200
    data = response.json()
    assert data["original_name"] == "ta_orig"
    assert data["new_name"] == "ta_orig_copy_1"

    get_resp = client.get(f"/api/v1/strategies/{data['new_name']}")
    assert get_resp.status_code == 200


def test_duplicate_strategy_explicit_name(make_client):
    client = make_client(router)
    _create(client, name="ta_orig2")

    response = client.post(
        "/api/v1/strategies/ta_orig2/duplicate", params={"new_name": "ta_clone"}
    )
    assert response.status_code == 200
    assert response.json()["new_name"] == "ta_clone"


def test_duplicate_strategy_name_collision(make_client):
    client = make_client(router)
    _create(client, name="ta_a")
    _create(client, name="ta_b")

    response = client.post(
        "/api/v1/strategies/ta_a/duplicate", params={"new_name": "ta_b"}
    )
    assert response.status_code == 400


def test_duplicate_missing_strategy_404(make_client):
    client = make_client(router)
    response = client.post("/api/v1/strategies/does_not_exist/duplicate")
    assert response.status_code == 404


def test_delete_strategy(make_client):
    client = make_client(router)
    _create(client, name="ta_delete_me")

    response = client.delete("/api/v1/strategies/ta_delete_me")
    assert response.status_code == 200

    get_resp = client.get("/api/v1/strategies/ta_delete_me")
    assert get_resp.status_code == 404


def test_delete_missing_strategy_404(make_client):
    client = make_client(router)
    response = client.delete("/api/v1/strategies/does_not_exist")
    assert response.status_code == 404

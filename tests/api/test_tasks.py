"""Tests for /tasks endpoints. TaskManager is real SQLite, isolated per test
via the autouse isolated_cresus_home fixture (CRESUS_DB_ROOT-less ~/.cresus
gets redirected to a tmp dir, so each test gets its own tasks.db).
"""

from api.routes.tasks import router


def _create(client, **overrides):
    payload = {"title": "Buy AAPL dip"}
    payload.update(overrides)
    return client.post("/api/v1/tasks", json=payload)


def test_create_task(make_client):
    client = make_client(router)
    response = _create(client, description="watch for entry", priority="High")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    task = data["task"]
    assert task["title"] == "Buy AAPL dip"
    assert task["description"] == "watch for entry"
    assert task["priority"] == "High"
    assert task["status"] == "To-Do"
    assert task["tags"] == []
    assert isinstance(task["id"], int)


def test_get_task_by_id(make_client):
    client = make_client(router)
    created = _create(client).json()["task"]

    response = client.get(f"/api/v1/tasks/{created['id']}")
    assert response.status_code == 200
    assert response.json()["task"]["id"] == created["id"]


def test_get_missing_task_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/tasks/999999")
    assert response.status_code == 404


def test_list_tasks_with_pagination(make_client):
    client = make_client(router)
    for i in range(5):
        _create(client, title=f"Task {i}")

    response = client.get("/api/v1/tasks?limit=2&offset=1")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert data["total"] == 5


def test_list_tasks_filter_by_status(make_client):
    client = make_client(router)
    _create(client, title="Open one", status="To-Do")
    _create(client, title="Done one", status="Done")

    response = client.get("/api/v1/tasks?status=Done")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["tasks"][0]["title"] == "Done one"


def test_list_tasks_filter_by_tags(make_client):
    client = make_client(router)
    _create(client, title="Tagged", tags=["urgent", "aapl"])
    _create(client, title="Untagged")

    response = client.get("/api/v1/tasks?tags=urgent")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["tasks"][0]["title"] == "Tagged"


def test_update_task(make_client):
    client = make_client(router)
    created = _create(client).json()["task"]

    response = client.put(
        f"/api/v1/tasks/{created['id']}",
        json={"title": "Buy AAPL dip", "status": "Done", "priority": "Low"},
    )
    assert response.status_code == 200
    task = response.json()["task"]
    assert task["status"] == "Done"
    assert task["priority"] == "Low"


def test_update_missing_task_404(make_client):
    client = make_client(router)
    response = client.put("/api/v1/tasks/999999", json={"title": "ghost"})
    assert response.status_code == 404


def test_delete_task(make_client):
    client = make_client(router)
    created = _create(client).json()["task"]

    response = client.delete(f"/api/v1/tasks/{created['id']}")
    assert response.status_code == 200

    response = client.get(f"/api/v1/tasks/{created['id']}")
    assert response.status_code == 404


def test_delete_missing_task_404(make_client):
    client = make_client(router)
    response = client.delete("/api/v1/tasks/999999")
    assert response.status_code == 404


def test_task_stats(make_client):
    client = make_client(router)
    _create(client, title="A", status="To-Do")
    _create(client, title="B", status="Done")

    response = client.get("/api/v1/tasks/stats/overview")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert isinstance(response.json()["stats"], dict)


def test_create_task_requires_title(make_client):
    client = make_client(router)
    response = client.post("/api/v1/tasks", json={"description": "no title"})
    assert response.status_code == 422

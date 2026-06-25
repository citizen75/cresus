"""Tests for /scheduler/jobs (cron management) endpoints.

CronManager() resolves cron.yml under {CRESUS_HOME}/.cresus/config, isolated
per test by the autouse isolated_cresus_home fixture. No app.state.cron_scheduler
is attached for most tests - get_cron_scheduler() degrades gracefully to None
for routes that only need to persist config (create/update/enable/disable/
delete), and /run + /reload correctly 500 without a live scheduler attached,
which we assert rather than spinning up a real APScheduler+background thread.
"""

from api.routes.scheduler import router


def _create_job(client, name="job_a", schedule="*/5 * * * *", target="heartbeat", **kw):
    params = {"name": name, "schedule": schedule, "target": target}
    params.update(kw)
    return client.post("/api/v1/scheduler/jobs", params=params)


def test_list_jobs_empty(make_client):
    client = make_client(router)
    response = client.get("/api/v1/scheduler/jobs")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["jobs"] == []
    assert data["total"] == 0


def test_create_and_get_job(make_client):
    client = make_client(router)
    response = _create_job(client, description="Heartbeat check")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    get_resp = client.get("/api/v1/scheduler/jobs/job_a")
    assert get_resp.status_code == 200
    job = get_resp.json()["job"]
    assert job["name"] == "job_a"
    assert job["schedule"] == "*/5 * * * *"
    assert job["target"] == "heartbeat"
    assert job["description"] == "Heartbeat check"
    assert job["enabled"] is False


def test_create_job_with_params_json(make_client):
    client = make_client(router)
    response = _create_job(client, params='{"universe": "cac40"}')
    assert response.status_code == 200

    job = client.get("/api/v1/scheduler/jobs/job_a").json()["job"]
    assert job["params"] == {"universe": "cac40"}


def test_create_job_invalid_params_json_400(make_client):
    client = make_client(router)
    response = _create_job(client, params="not-json")
    assert response.status_code == 400


def test_create_job_enabled_without_scheduler_still_saves(make_client):
    """enabled=True with no cron_scheduler attached should still persist the
    job config - syncing to a live scheduler is best-effort."""
    client = make_client(router)
    response = _create_job(client, enabled=True)
    assert response.status_code == 200

    job = client.get("/api/v1/scheduler/jobs/job_a").json()["job"]
    assert job["enabled"] is True


def test_get_missing_job_404(make_client):
    client = make_client(router)
    response = client.get("/api/v1/scheduler/jobs/ghost")
    assert response.status_code == 404


def test_update_job(make_client):
    client = make_client(router)
    _create_job(client)

    response = client.put(
        "/api/v1/scheduler/jobs/job_a",
        params={"schedule": "0 9 * * *", "description": "Updated"},
    )
    assert response.status_code == 200

    job = client.get("/api/v1/scheduler/jobs/job_a").json()["job"]
    assert job["schedule"] == "0 9 * * *"
    assert job["description"] == "Updated"
    # target untouched by partial update
    assert job["target"] == "heartbeat"


def test_update_missing_job_400(make_client):
    client = make_client(router)
    response = client.put("/api/v1/scheduler/jobs/ghost", params={"schedule": "* * * * *"})
    assert response.status_code == 400


def test_enable_and_disable_job(make_client):
    client = make_client(router)
    _create_job(client)

    response = client.post("/api/v1/scheduler/jobs/job_a/enable")
    assert response.status_code == 200
    assert client.get("/api/v1/scheduler/jobs/job_a").json()["job"]["enabled"] is True

    response = client.post("/api/v1/scheduler/jobs/job_a/disable")
    assert response.status_code == 200
    assert client.get("/api/v1/scheduler/jobs/job_a").json()["job"]["enabled"] is False


def test_enable_missing_job_400(make_client):
    client = make_client(router)
    response = client.post("/api/v1/scheduler/jobs/ghost/enable")
    assert response.status_code == 400


def test_duplicate_job(make_client):
    client = make_client(router)
    _create_job(client)

    response = client.post(
        "/api/v1/scheduler/jobs/job_a/duplicate", params={"new_name": "job_b"}
    )
    assert response.status_code == 200
    assert client.get("/api/v1/scheduler/jobs/job_b").status_code == 200


def test_duplicate_missing_new_name_422(make_client):
    client = make_client(router)
    _create_job(client)
    response = client.post("/api/v1/scheduler/jobs/job_a/duplicate")
    assert response.status_code == 422


def test_delete_job(make_client):
    client = make_client(router)
    _create_job(client)

    response = client.delete("/api/v1/scheduler/jobs/job_a")
    assert response.status_code == 200
    assert client.get("/api/v1/scheduler/jobs/job_a").status_code == 404


def test_delete_missing_job_400(make_client):
    client = make_client(router)
    response = client.delete("/api/v1/scheduler/jobs/ghost")
    assert response.status_code == 400


def test_run_job_without_scheduler_500(make_client):
    client = make_client(router)
    _create_job(client)

    response = client.post("/api/v1/scheduler/jobs/job_a/run")
    assert response.status_code == 500


def test_run_missing_job_404(make_client):
    client = make_client(router)
    response = client.post("/api/v1/scheduler/jobs/ghost/run")
    assert response.status_code == 404


def test_reload_without_scheduler_500(make_client):
    client = make_client(router)
    response = client.post("/api/v1/scheduler/reload")
    assert response.status_code == 500


def test_job_logs_for_unknown_job_returns_empty(make_client, isolated_cresus_home):
    client = make_client(router)
    response = client.get("/api/v1/scheduler/jobs/never_ran/logs")
    assert response.status_code == 200
    data = response.json()
    assert data["logs"] == []
    assert data["total_lines"] == 0


def test_list_all_logs_empty(make_client, isolated_cresus_home):
    client = make_client(router)
    response = client.get("/api/v1/scheduler/logs")
    assert response.status_code == 200
    assert response.json()["logs"] == {}
    assert response.json()["total_tasks"] == 0


def test_list_all_logs_with_existing_log_file(make_client, isolated_cresus_home):
    log_dir = isolated_cresus_home / ".cresus" / "db" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "job_a.log").write_text("line one\nline two\n")

    client = make_client(router)
    response = client.get("/api/v1/scheduler/logs")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tasks"] == 1
    assert "job_a" in data["logs"]

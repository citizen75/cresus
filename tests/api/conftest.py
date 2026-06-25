"""Shared fixtures for the src/api test suite.

Every test is isolated from the real ~/.cresus directory by patching
Path.home() to a per-test tmp directory. Managers under tools/* resolve their
storage path either via utils.env.get_db_root() (which falls back to
Path.home()/".cresus"/"db" unless CRESUS_DB_ROOT is set) or by calling
Path.home() directly - patching home alone covers both, so tests never read
or write production data.
"""

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.fixture(autouse=True)
def isolated_cresus_home(tmp_path, monkeypatch):
    """Redirect ~/.cresus (and CRESUS_DB_ROOT/CONFIG_ROOT fallbacks) to a tmp dir."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.delenv("CRESUS_DB_ROOT", raising=False)
    monkeypatch.delenv("CRESUS_CONFIG_ROOT", raising=False)
    monkeypatch.delenv("CRESUS_ENV_FILE", raising=False)
    return fake_home


def _make_client(*routers, prefix: str = "/api/v1") -> TestClient:
    """Build a minimal FastAPI app mounting only the given router(s).

    Deliberately avoids api.app.create_app(): that factory starts real
    APScheduler background threads (legacy data-fetch + cron scheduler) which
    never get torn down between tests and aren't needed to exercise a single
    router's request/response contract.
    """
    app = FastAPI()
    for router in routers:
        app.include_router(router, prefix=prefix)
    return TestClient(app)


@pytest.fixture
def make_client():
    """Fixture form of _make_client, for use as `make_client(router)` in tests."""
    return _make_client

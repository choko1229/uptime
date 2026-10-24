from unittest.mock import patch

import pytest

import app.db as db_module
import app.routers.setup as setup_router
import app.runtime_config as runtime_config_module


@pytest.fixture
def unconfigured_client():
    """A TestClient with the database intentionally left unconfigured."""
    previous_engine = db_module.engine
    previous_session_maker = db_module.async_session_maker
    db_module.engine = None
    db_module.async_session_maker = None
    try:
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as test_client:
            yield test_client
    finally:
        db_module.engine = previous_engine
        db_module.async_session_maker = previous_session_maker


def test_root_redirects_to_setup_when_unconfigured(unconfigured_client):
    r = unconfigured_client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/setup"


def test_admin_redirects_to_setup_when_unconfigured(unconfigured_client):
    r = unconfigured_client.get("/admin", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/setup"


def test_setup_form_renders_when_unconfigured(unconfigured_client):
    r = unconfigured_client.get("/setup")
    assert r.status_code == 200
    assert "初期セットアップ" in r.text


def test_setup_form_redirects_when_already_configured(client):
    # `client` fixture (from conftest) has already configured the database.
    r = client.get("/setup", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/admin/login"


def test_setup_submit_reports_connection_error(unconfigured_client):
    r = unconfigured_client.post(
        "/setup",
        data={
            "host": "this-host-does-not-exist.invalid",
            "port": "3306",
            "name": "uptime",
            "user": "uptime",
            "password": "uptime",
        },
    )
    assert r.status_code == 400
    assert "接続できませんでした" in r.text
    # Must not have marked the database as configured on failure.
    assert not db_module.is_configured()


def test_setup_submit_success_creates_admin_and_configures_db(
    unconfigured_client, tmp_path, monkeypatch
):
    """Exercises the full first-run happy path against a real (sqlite) database:
    connectivity check -> save config -> configure_database -> run real Alembic
    migrations -> auto-create the sole admin account. Only the DB dialect is
    swapped for sqlite since a real MySQL isn't available in this environment;
    everything else runs unmocked.
    """
    db_file = tmp_path / "setup_test.db"

    def fake_build_database_url(config, *, driver="mysql+aiomysql"):
        if "pymysql" in driver:
            return f"sqlite:///{db_file}"
        return f"sqlite+aiosqlite:///{db_file}"

    monkeypatch.setattr(runtime_config_module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(runtime_config_module, "DATABASE_CONFIG_PATH", tmp_path / "database.json")

    with patch.object(setup_router, "build_database_url", side_effect=fake_build_database_url):
        r = unconfigured_client.post(
            "/setup",
            data={
                "host": "ignored",
                "port": "3306",
                "name": "ignored",
                "user": "ignored",
                "password": "ignored",
            },
            follow_redirects=False,
        )

    assert r.status_code == 303, r.text
    assert r.headers["location"] == "/admin/login?setup=done"
    assert db_module.is_configured()
    assert (tmp_path / "database.json").exists()

    # A real admin user must have been created with a random password.
    import sqlite3

    conn = sqlite3.connect(db_file)
    rows = conn.execute("SELECT username FROM users").fetchall()
    conn.close()
    assert rows == [("admin",)]

    # A second /setup submission must be a no-op redirect, not a re-creation.
    r = unconfigured_client.post("/setup", data={}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/admin/login"

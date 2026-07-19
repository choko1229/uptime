import pytest

from app.auth import hash_password
from app.models import User


@pytest.fixture
async def admin_user(db_session):
    db_session.add(User(username="admin", password_hash=hash_password("password123")))
    await db_session.commit()


def test_admin_requires_login(client, admin_user):
    r = client.get("/admin", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/admin/login"


def test_login_wrong_password_rejected(client, admin_user):
    r = client.post("/admin/login", data={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_full_monitor_and_incident_flow(client, admin_user):
    r = client.post(
        "/admin/login",
        data={"username": "admin", "password": "password123"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    r = client.post(
        "/admin/monitors/new",
        data={
            "name": "Example site",
            "type": "webpage",
            "url": "https://example.com",
            "check_interval_seconds": "60",
            "failure_threshold": "2",
            "enabled": "on",
            "show_on_status_page": "on",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    r = client.get("/admin")
    assert "Example site" in r.text

    r = client.post(
        "/admin/incidents/new",
        data={
            "title": "Example site is down",
            "monitor_id": "1",
            "status": "investigating",
            "description": "Investigating a 500 error.",
            "is_published": "on",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    r = client.get("/incidents")
    assert "Example site is down" in r.text

    r = client.post(
        "/admin/incidents/1/update",
        data={"status": "resolved", "message": "Fixed."},
        follow_redirects=False,
    )
    assert r.status_code == 303
    r = client.get("/admin/incidents/1")
    assert "resolved" in r.text
    assert "Fixed." in r.text

    r = client.post("/admin/monitors/1/delete", follow_redirects=False)
    assert r.status_code == 303
    r = client.get("/admin")
    assert "Example site" not in r.text

import pytest

from app.auth import hash_password
from app.models import User


@pytest.fixture
async def logged_in_client(client, db_session):
    db_session.add(User(username="admin", password_hash=hash_password("password123")))
    await db_session.commit()
    client.post(
        "/admin/login",
        data={"username": "admin", "password": "password123"},
        follow_redirects=False,
    )
    return client


def test_settings_form_shows_defaults(logged_in_client):
    r = logged_in_client.get("/admin/settings")
    assert r.status_code == 200
    assert "Uptime Monitor" in r.text


def test_settings_update_persists(logged_in_client):
    r = logged_in_client.post(
        "/admin/settings",
        data={
            "site_title": "My Status Page",
            "pagespeed_api_key": "test-key",
            "smtp_host": "smtp.example.com",
            "smtp_port": "465",
            "smtp_username": "bot@example.com",
            "smtp_password": "secret",
            "smtp_from_address": "bot@example.com",
            "smtp_use_tls": "on",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    r = logged_in_client.get("/admin/settings")
    assert "My Status Page" in r.text
    assert "smtp.example.com" in r.text

    # site title should now also show on the public status page
    r = logged_in_client.get("/")
    assert "My Status Page" in r.text


def test_password_change_requires_matching_and_length(logged_in_client):
    r = logged_in_client.post(
        "/admin/settings/password",
        data={"new_password": "short", "confirm_password": "short"},
    )
    assert r.status_code == 400
    assert "8文字以上" in r.text

    r = logged_in_client.post(
        "/admin/settings/password",
        data={"new_password": "newpassword123", "confirm_password": "different"},
    )
    assert r.status_code == 400


def test_password_change_success_and_relogin(logged_in_client):
    r = logged_in_client.post(
        "/admin/settings/password",
        data={"new_password": "newpassword123", "confirm_password": "newpassword123"},
    )
    assert r.status_code == 200
    assert "パスワードを変更しました" in r.text

    logged_in_client.post("/admin/logout", follow_redirects=False)

    r = logged_in_client.post(
        "/admin/login", data={"username": "admin", "password": "newpassword123"}, follow_redirects=False
    )
    assert r.status_code == 303

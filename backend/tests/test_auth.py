"""Login, refresh, pembatas percobaan, otorisasi peran, dan audit trail."""

import pytest

from app.models.enums import Role
from tests.conftest import PASSWORD, USERS, login, query

PROTECTED = [
    ("post", "/api/extract-tender-metadata"),
    ("post", "/api/generate-tender"),
    ("get", "/api/kb/list?collection=rks_kb"),
    ("get", "/api/auth/me"),
]


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_protected_endpoints_require_login(client, method, path):
    assert getattr(client, method)(path).status_code == 401


def test_invalid_token_rejected(client):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer bukan.token.sah"})
    assert res.status_code == 401


def test_login_success_returns_profile_and_refresh_cookie(client):
    res = client.post("/api/auth/login", json={"username": USERS[Role.FPP].upper(), "password": PASSWORD})
    assert res.status_code == 200
    body = res.json()
    assert body["user"]["role"] == "FPP"
    assert "password_hash" not in body["user"]
    assert "itec_refresh" in res.cookies

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.json()["username"] == USERS[Role.FPP]


def test_login_failure_is_generic_and_audited(client):
    unknown = client.post("/api/auth/login", json={"username": "tidak_ada", "password": "salah"})
    wrong = client.post("/api/auth/login", json={"username": USERS[Role.ADMIN], "password": "salah"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]
    rows = query("SELECT count(*) FROM procurement_audit_trail WHERE tipe_aksi = 'LOGIN_GAGAL'")
    assert rows[0][0] >= 2


def test_login_locked_after_repeated_failures(client):
    for _ in range(5):
        client.post("/api/auth/login", json={"username": USERS[Role.AUDITOR], "password": "salah"})
    res = client.post("/api/auth/login", json={"username": USERS[Role.AUDITOR], "password": PASSWORD})
    assert res.status_code == 429
    assert "Retry-After" in res.headers


def test_refresh_issues_new_access_token(client):
    login(client, Role.PROCUREMENT)  # menyimpan cookie refresh di client
    res = client.post("/api/auth/refresh")
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "PROCUREMENT"


def test_refresh_without_cookie_rejected(client):
    assert client.post("/api/auth/refresh").status_code == 401


def test_logout_clears_refresh_cookie(client):
    login(client, Role.FPP)
    assert client.post("/api/auth/logout").status_code == 204
    assert client.post("/api/auth/refresh").status_code == 401


@pytest.mark.parametrize("role", [Role.AUDITOR, Role.APPROVER])
def test_roles_without_drafting_access_cannot_extract(client, role):
    res = client.post("/api/extract-tender-metadata", headers=login(client, role))
    assert res.status_code == 403


def test_auditor_cannot_generate_documents(client):
    res = client.post("/api/generate-tender", data={"nama_pengadaan": "X"}, headers=login(client, Role.AUDITOR))
    assert res.status_code == 403


@pytest.mark.parametrize("role", [Role.FPP, Role.APPROVER, Role.AUDITOR])
def test_only_kb_managers_can_delete_kb_documents(client, role):
    res = client.request(
        "DELETE",
        "/api/kb/delete",
        data={"collection": "rks_kb", "filename": "x.pdf"},
        headers=login(client, role),
    )
    assert res.status_code == 403


def test_successful_login_is_audited_with_user(client):
    login(client, Role.APPROVER)
    rows = query(
        "SELECT count(*) FROM procurement_audit_trail a JOIN app_user u ON u.id = a.user_id "
        "WHERE a.tipe_aksi = 'LOGIN' AND u.username = :u",
        u=USERS[Role.APPROVER],
    )
    assert rows[0][0] >= 1

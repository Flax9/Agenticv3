"""Validasi input & health (tidak membutuhkan LLM maupun Qdrant)."""

import pytest

from app.api.tender_routes import _safe_name
from app.models.enums import Role
from tests.conftest import login


@pytest.fixture
def admin(client):
    return login(client, Role.ADMIN)


def test_health_reports_status_without_secrets(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert set(body) == {"status", "llm_configured", "qdrant_configured"}


def test_extract_requires_at_least_one_file(client, admin):
    res = client.post("/api/extract-tender-metadata", data={"tanggal": "19 Oktober 2026"}, headers=admin)
    assert res.status_code == 400


def test_extract_rejects_unsupported_extension(client, admin):
    res = client.post(
        "/api/extract-tender-metadata",
        files={"file_boq": ("boq.exe", b"MZ fake", "application/octet-stream")},
        headers=admin,
    )
    assert res.status_code == 415


def test_extract_rejects_excel_as_rks(client, admin):
    res = client.post(
        "/api/extract-tender-metadata",
        files={"file_rks": ("rks.xlsx", b"fake", "application/vnd.ms-excel")},
        headers=admin,
    )
    assert res.status_code == 415


def test_extract_rejects_empty_file(client, admin):
    res = client.post(
        "/api/extract-tender-metadata", files={"file_rks": ("rks.pdf", b"", "application/pdf")}, headers=admin
    )
    assert res.status_code == 400


def test_kb_list_rejects_unknown_collection(client, admin):
    res = client.get("/api/kb/list", params={"collection": "tidak_ada"}, headers=admin)
    assert res.status_code == 400


def test_amendemen_rejects_invalid_json(client, admin):
    res = client.post("/api/generate-amendemen", data={"detail_perubahan_json": "{bukan json"}, headers=admin)
    assert res.status_code == 422


def test_docs_hidden_when_not_debug(client):
    assert client.get("/docs").status_code == 404


def test_safe_name_strips_path_and_symbols():
    assert _safe_name("../Paket <A>/B") == "___Paket__A__B"

"""Penyesuaian backend: kesiapan layanan, batas laju chat, job tersimpan di database, checkpointer agent."""

import uuid

import pytest

from app.api import chat_routes, health_routes
from app.core import checkpointer
from app.core.jobs import INTERRUPTED_MESSAGE, jobs
from app.core.rate_limit import chat_limiter
from app.models.enums import Role
from tests.conftest import execute, login, query
from tests.test_chat import _new_session, runner  # noqa: F401  (fixture)
from tests.test_dataset import dataset, wait_job  # noqa: F401  (fixture)


def test_ready_reports_database(client, monkeypatch):
    async def llm_ok():
        return "ok"

    monkeypatch.setattr(health_routes, "_check_llm", llm_ok)  # tanpa panggilan jaringan sungguhan
    res = client.get("/api/health/ready")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok" and body["database"] == "ok"
    assert "qdrant" in body and body["llm"] == "ok"


def test_ready_reports_rejected_llm_key_without_failing(client, monkeypatch):
    async def rejected():
        return "kunci ditolak atau kedaluwarsa"

    monkeypatch.setattr(health_routes, "_check_llm", rejected)
    res = client.get("/api/health/ready")
    # Kunci LLM yang mati tidak membuat layanan "tidak siap": hanya fitur chat yang terdampak
    assert res.status_code == 200
    assert res.json()["llm"] == "kunci ditolak atau kedaluwarsa"


def test_ready_returns_503_without_leaking_details(client, monkeypatch):
    async def llm_ok():
        return "ok"

    monkeypatch.setattr(health_routes, "_check_llm", llm_ok)

    async def broken():
        raise ConnectionError("postgresql://user:rahasia@host/db")

    monkeypatch.setattr(health_routes, "_check_database", broken)
    res = client.get("/api/health/ready")
    assert res.status_code == 503
    assert res.json()["database"] == "gagal (ConnectionError)"
    assert "rahasia" not in res.text


def test_chat_rate_limit(client, runner, monkeypatch):  # noqa: F811
    monkeypatch.setattr(chat_limiter, "limit", 2)
    fpp = login(client, Role.FPP)
    sid = _new_session(client, fpp)["id"]
    url = f"/api/chat/sessions/{sid}/messages"
    assert client.post(url, json={"content": "satu"}, headers=fpp).status_code == 200
    assert client.post(url, json={"content": "dua"}, headers=fpp).status_code == 200
    res = client.post(url, json={"content": "tiga"}, headers=fpp)
    assert res.status_code == 429
    assert int(res.headers["Retry-After"]) >= 1
    # Batas berlaku per pengguna, bukan global
    other = login(client, Role.PROCUREMENT)
    sid2 = _new_session(client, other)["id"]
    assert (
        client.post(f"/api/chat/sessions/{sid2}/messages", json={"content": "halo"}, headers=other).status_code == 200
    )


def test_job_result_survives_restart(client, dataset):  # noqa: F811
    (dataset / "rks_kb").mkdir()
    (dataset / "rks_kb" / "a.pdf").write_bytes(b"%PDF-1.4 isi")
    headers = login(client, Role.PROCUREMENT)
    job_id = client.post("/api/dataset/sync", headers=headers).json()["id"]
    assert wait_job(client, headers, job_id)["status"] == "selesai"

    row = query("SELECT status, finished_at FROM background_job WHERE id = :i", i=uuid.UUID(job_id))[0]
    assert row.status == "selesai" and row.finished_at is not None

    # Meniru restart: memori proses kosong, status harus tetap terbaca dari database
    jobs._jobs.clear()
    again = client.get(f"/api/jobs/{job_id}", headers=headers)
    assert again.status_code == 200 and again.json()["status"] == "selesai"
    assert again.json()["result"]["ditambah"] == ["rks_kb/a.pdf"]
    # Pemilik tetap dibatasi setelah dibaca dari database
    assert client.get(f"/api/jobs/{job_id}", headers=login(client, Role.FPP)).status_code == 404


def test_interrupted_job_is_marked_failed(client):
    job_id = uuid.uuid4()
    execute(
        "INSERT INTO background_job (id, kind, user_id, status) "
        "SELECT :i, 'sinkron_dataset', id, 'berjalan' FROM app_user WHERE username = :u",
        i=job_id,
        u="uji_admin",
    )
    assert client.portal.call(jobs.fail_interrupted) >= 1
    row = query("SELECT status, error FROM background_job WHERE id = :i", i=job_id)[0]
    assert row.status == "gagal" and row.error == INTERRUPTED_MESSAGE


def test_checkpointer_uses_postgres():
    from langgraph.checkpoint.postgres import PostgresSaver

    saver = checkpointer.make_checkpointer()
    assert isinstance(saver, PostgresSaver)
    saver.conn.close()


def test_checkpointer_memory_when_configured(monkeypatch):
    from langgraph.checkpoint.memory import MemorySaver

    monkeypatch.setattr(checkpointer.settings, "agent_checkpointer", "memory")
    assert isinstance(checkpointer.make_checkpointer(), MemorySaver)


def test_checkpointer_falls_back_when_database_unreachable(monkeypatch):
    from langgraph.checkpoint.memory import MemorySaver

    monkeypatch.setattr(checkpointer.settings, "database_url", "postgresql+asyncpg://x:y@127.0.0.1:1/none")
    assert isinstance(checkpointer.make_checkpointer(), MemorySaver)


def test_nul_character_is_rejected_not_500(client, runner):  # noqa: F811
    res = client.post("/api/auth/login", json={"username": "a\u0000b", "password": "x"})
    assert res.status_code == 422
    fpp = login(client, Role.FPP)
    sid = _new_session(client, fpp)["id"]
    res = client.post(f"/api/chat/sessions/{sid}/messages", json={"content": "halo\u0000"}, headers=fpp)
    assert res.status_code == 422


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (RuntimeError("UnauthorizedResponseError: API key expired."), "OPENROUTER_API_KEY"),
        (RuntimeError("429 rate limit exceeded"), "sibuk"),
        (ConnectionError("Connection refused"), "Tidak dapat terhubung"),
        (ValueError("sesuatu yang aneh"), "hubungi administrator"),
    ],
)
def test_agent_error_message_is_friendly(error, expected):
    reply = chat_routes._agent_error_message(error)
    assert expected in reply
    assert str(error) not in reply  # detail teknis tidak ditampilkan ke pengguna

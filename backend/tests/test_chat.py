"""Sesi chat & draf dengan agent palsu (tanpa LLM/Qdrant)."""

import pytest

from app.api import chat_routes, dataset_routes
from app.config import settings
from app.main import app
from app.models.enums import Role
from app.services import drafts
from app.services.chat.agent_runner import AgentTurn
from tests.conftest import login, query
from tests.test_dataset import FakeStore, wait_job

DRAFT = {"cover_page": {"judul_pekerjaan": "Tangki Air"}, "bab": [{"nomor": "I", "judul": "Umum", "sub_bab": []}]}


class FakeRunner:
    """Meniru alur agent RKS: minta BoQ → tanya judul → draf (review) → ekspor."""

    def __init__(self, docx_path):
        self.docx_path = docx_path
        self.stage: dict[str, str] = {}
        self.received: list[str] = []
        self.fail = False

    def is_skip_answer(self, text):
        return text.strip().lower() in {"skip", "lewati"}

    def awaiting(self, thread_id):
        return {"boq": "upload_boq", "review": "review_rks"}.get(self.stage.get(thread_id))

    def run_turn(self, thread_id, text, on_event=None):
        if self.fail:
            raise RuntimeError("LLM timeout")
        self.received.append(text)
        if on_event:
            on_event("progress", {"node": "route_question"})
            on_event("token", {"text": "Halo"})
        stage = self.stage.get(thread_id)
        if stage is None:
            self.stage[thread_id] = "boq"
            return AgentTurn(["📎 Apakah Anda memiliki BoQ?"], "upload_boq", None, None, None)
        if stage == "boq":
            self.stage[thread_id] = "judul"
            return AgentTurn(["✅ Melanjutkan.", "Apa judul pekerjaan?"], None, {}, None, None)
        if stage == "judul":
            self.stage[thread_id] = "review"
            fields = {"judul_pekerjaan": text}
            return AgentTurn(["📄 Draf RKS telah dibuat!", "Setuju?"], "review_rks", fields, DRAFT, None)
        self.stage[thread_id] = "done"
        return AgentTurn([f"✅ Dokumen RKS berhasil dibuat! `{self.docx_path}`"], None, None, None, self.docx_path)


@pytest.fixture
def runner(tmp_path, monkeypatch):
    docx = tmp_path / "agent_output.docx"
    docx.write_bytes(b"PK fake docx")
    monkeypatch.setattr(drafts, "DRAFTS_DIR", tmp_path / "drafts")
    fake = FakeRunner(docx)
    app.dependency_overrides[chat_routes.get_rks_runner] = lambda: fake
    yield fake
    app.dependency_overrides.pop(chat_routes.get_rks_runner, None)


def _new_session(client, headers, tipe="rks"):
    res = client.post("/api/chat/sessions", json={"tipe_dokumen": tipe}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def _send(client, headers, sid, content="", **extra):
    res = client.post(f"/api/chat/sessions/{sid}/messages", json={"content": content, **extra}, headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def test_session_access_rules(client, runner):
    fpp = login(client, Role.FPP)
    s = _new_session(client, fpp)
    assert s["tipe_dokumen"] == "rks" and "draf baru" in s["nama_pengadaan"]
    assert client.get("/api/chat/sessions", headers=fpp).json()[0]["id"] == s["id"]

    # Peran peninjau boleh melihat, tetapi tidak boleh menulis di sesi milik orang lain
    auditor = login(client, Role.AUDITOR)
    assert client.get(f"/api/chat/sessions/{s['id']}", headers=auditor).status_code == 200
    procurement = login(client, Role.PROCUREMENT)
    res = client.post(f"/api/chat/sessions/{s['id']}/messages", json={"content": "halo"}, headers=procurement)
    assert res.status_code == 404
    # AUDITOR tidak bisa membuat sesi
    assert client.post("/api/chat/sessions", json={"tipe_dokumen": "rks"}, headers=auditor).status_code == 403


def test_rks_flow_creates_versioned_draft_and_docx(client, runner):
    fpp = login(client, Role.FPP)
    sid = _new_session(client, fpp)["id"]

    turn = _send(client, fpp, sid, "Buatkan RKS")
    assert turn["awaiting"] == "upload_boq"

    # Teks bebas saat agent meminta BoQ tidak diteruskan (agent akan menganggapnya path berkas server)
    turn = _send(client, fpp, sid, "C:/Windows/system.ini")
    assert runner.received == ["Buatkan RKS"]
    assert "lewati" in turn["messages"][-1]["content"]

    _send(client, fpp, sid, "lewati")
    turn = _send(client, fpp, sid, "Pembangunan Tangki Air")
    assert turn["awaiting"] == "review_rks"
    assert turn["nama_pengadaan"] == "Pembangunan Tangki Air"
    assert turn["draft"]["versi"] == "v1.0" and turn["draft"]["konten_json"] == DRAFT
    assert turn["draft"]["has_docx"] is False
    assert turn["messages"][-1]["artifacts_payload"]["draft_id"] == turn["draft"]["id"]

    turn = _send(client, fpp, sid, "setuju")
    draft_id = turn["draft"]["id"]
    assert turn["draft"]["has_docx"] is True and turn["draft"]["versi"] == "v1.0"

    res = client.get(f"/api/drafts/{draft_id}/download", headers=fpp)
    assert res.status_code == 200 and res.content == b"PK fake docx"
    assert client.get(f"/api/drafts/{draft_id}/download", headers=login(client, Role.AUDITOR)).status_code == 404

    detail = client.get(f"/api/chat/sessions/{sid}", headers=fpp).json()
    roles = [m["role"] for m in detail["messages"]]
    assert roles[:3] == ["user", "assistant", "user"]
    assert detail["messages"][0]["content"] == "Buatkan RKS"
    assert detail["draft"]["id"] == draft_id
    assert query("SELECT 1 FROM procurement_audit_trail WHERE tipe_aksi = 'GENERATE_DOCX' AND modul_terkait = 'CHAT'")


def test_boq_from_dataset_is_passed_as_path(client, runner, tmp_path, monkeypatch):
    dataset = tmp_path / "dataset"
    (dataset / "paket").mkdir(parents=True)
    (dataset / "paket" / "BoQ Siantar.pdf").write_bytes(b"%PDF boq")
    monkeypatch.setattr(settings, "dataset_dir", dataset)
    monkeypatch.setattr(dataset_routes, "Vector_Store", FakeStore)
    admin = login(client, Role.ADMIN)
    wait_job(client, admin, client.post("/api/dataset/sync", headers=admin).json()["id"])
    files = client.get("/api/dataset/files", params={"acuan": True}, headers=login(client, Role.FPP)).json()["files"]
    boq = next(f for f in files if f["nama_file"] == "BoQ Siantar.pdf")

    fpp = login(client, Role.FPP)
    sid = _new_session(client, fpp)["id"]
    # Lampiran hanya diterima saat agent meminta BoQ
    res = client.post(f"/api/chat/sessions/{sid}/messages", json={"dataset_file_id": boq["id"]}, headers=fpp)
    assert res.status_code == 400

    _send(client, fpp, sid, "Buatkan RKS")
    turn = _send(client, fpp, sid, dataset_file_id=boq["id"])
    assert runner.received[-1] == str((dataset / "paket" / "BoQ Siantar.pdf").resolve())
    assert turn["messages"][0]["content"] == "📎 Memakai BoQ dari drive: paket/BoQ Siantar.pdf"


def test_agent_error_is_saved_as_message(client, runner):
    fpp = login(client, Role.FPP)
    sid = _new_session(client, fpp)["id"]
    runner.fail = True
    turn = _send(client, fpp, sid, "Buatkan RKS")
    assert turn["messages"][-1]["artifacts_payload"] == {"error": True}
    assert "Tidak dapat terhubung" in turn["messages"][-1]["content"]  # pesan ramah, bukan galat mentah


def test_non_rks_session_explains_agent_not_available(client, runner):
    fpp = login(client, Role.FPP)
    sid = _new_session(client, fpp, "kontrak")["id"]
    turn = _send(client, fpp, sid, "Buatkan kontrak")
    assert "belum tersedia" in turn["messages"][-1]["content"]
    assert runner.received == []


def _sse_events(text: str) -> list[tuple[str, dict]]:
    import json

    events = []
    for block in text.strip().split("\n\n"):
        if block.startswith(":"):  # komentar heartbeat
            continue
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_stream_reports_progress_tokens_and_result(client, runner):
    fpp = login(client, Role.FPP)
    sid = _new_session(client, fpp)["id"]
    res = client.post(f"/api/chat/sessions/{sid}/stream", json={"content": "Buatkan RKS"}, headers=fpp)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    assert res.headers["x-accel-buffering"] == "no"

    events = _sse_events(res.text)
    kinds = [k for k, _ in events]
    assert kinds == ["progress", "token", "done"]
    assert events[0][1] == {"node": "route_question", "label": "Memahami pertanyaan"}
    done = events[-1][1]
    assert done["awaiting"] == "upload_boq"
    assert [m["role"] for m in done["messages"]] == ["user", "assistant"]

    # Pesan tersimpan sama seperti endpoint non-stream
    detail = client.get(f"/api/chat/sessions/{sid}", headers=fpp).json()
    assert [m["content"] for m in detail["messages"]] == ["Buatkan RKS", "📎 Apakah Anda memiliki BoQ?"]


def test_stream_validation_errors_are_plain_http(client, runner):
    fpp = login(client, Role.FPP)
    sid = _new_session(client, fpp)["id"]
    res = client.post(f"/api/chat/sessions/{sid}/stream", json={"content": "  "}, headers=fpp)
    assert res.status_code == 422
    # Lampiran saat agent tidak meminta BoQ ditolak sebelum stream dimulai, dan lock dilepas kembali
    res = client.post(
        f"/api/chat/sessions/{sid}/stream",
        json={"dataset_file_id": "00000000-0000-0000-0000-000000000000"},
        headers=fpp,
    )
    assert res.status_code == 400
    assert _send(client, fpp, sid, "Buatkan RKS")["awaiting"] == "upload_boq"


def test_stream_sends_heartbeat_while_agent_is_silent(client, runner, monkeypatch):
    import time

    monkeypatch.setattr(chat_routes, "HEARTBEAT_SECONDS", 0.05)
    original = runner.run_turn

    def slow_turn(thread_id, text, on_event=None):
        time.sleep(0.3)
        return original(thread_id, text, on_event)

    monkeypatch.setattr(runner, "run_turn", slow_turn)
    fpp = login(client, Role.FPP)
    sid = _new_session(client, fpp)["id"]
    res = client.post(f"/api/chat/sessions/{sid}/stream", json={"content": "Buatkan RKS"}, headers=fpp)
    assert ": ping" in res.text
    assert res.text.rstrip().splitlines()[-2] == "event: done"

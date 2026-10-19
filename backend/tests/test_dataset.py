"""Sinkronisasi folder dataset (drive) ke Knowledge Base, dengan Qdrant palsu."""

import os
import time
from typing import ClassVar

import pytest

from app.api import dataset_routes
from app.config import settings
from app.models.enums import Role
from tests.conftest import execute, login, query


class FakeStore:
    calls: ClassVar[list[tuple]] = []

    def __init__(self, collection: str):
        self.collection = collection

    def ingest_bytes(self, content: bytes, filename: str) -> int:
        if content.startswith(b"RUSAK"):
            raise ValueError("PDF tidak terbaca")
        FakeStore.calls.append(("ingest", self.collection, filename))
        return 3

    def delete_source(self, filename: str) -> None:
        FakeStore.calls.append(("delete", self.collection, filename))


@pytest.fixture
def dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "dataset_dir", tmp_path)
    monkeypatch.setattr(dataset_routes, "Vector_Store", FakeStore)
    FakeStore.calls = []
    execute("DELETE FROM procurement_dataset_file")
    return tmp_path


def _write(root, rel: str, content: bytes = b"%PDF-1.4 isi"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def wait_job(client, headers, job_id: str, timeout: float = 30) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}", headers=headers).json()
        if job["status"] != "berjalan":
            return job
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} tidak selesai dalam {timeout} detik")


def _sync(client, role=Role.PROCUREMENT):
    headers = login(client, role)
    res = client.post("/api/dataset/sync", headers=headers)
    assert res.status_code == 202, res.text
    job = wait_job(client, headers, res.json()["id"])
    assert job["status"] == "selesai", job
    assert job["progress"]["selesai"] == job["progress"]["total"]
    return job["result"]


def test_sync_requires_kb_manager(client, dataset):
    res = client.post("/api/dataset/sync", headers=login(client, Role.FPP))
    assert res.status_code == 403


def test_sync_reports_unconfigured_dataset(client, monkeypatch):
    monkeypatch.setattr(settings, "dataset_dir", None)
    res = client.post("/api/dataset/sync", headers=login(client, Role.ADMIN))
    assert res.status_code == 503


def test_sync_ingests_collections_and_keeps_references(client, dataset):
    _write(dataset, "rks_kb/RKS Tangki.pdf")
    _write(dataset, "contract_kb/sub/Kontrak.pdf")
    _write(dataset, "paket_siantar/BoQ.xlsx", b"excel")
    _write(dataset, "rks_kb/catatan.docx", b"word")  # format tidak dikenal: diabaikan
    _write(dataset, "rks_kb/~$RKS Tangki.pdf")  # berkas kunci Office: diabaikan

    report = _sync(client)
    assert sorted(report["ditambah"]) == [
        "contract_kb/sub/Kontrak.pdf",
        "paket_siantar/BoQ.xlsx",
        "rks_kb/RKS Tangki.pdf",
    ]
    assert sorted(FakeStore.calls) == [("ingest", "contract_kb", "Kontrak.pdf"), ("ingest", "rks_kb", "RKS Tangki.pdf")]

    files = client.get("/api/dataset/files", headers=login(client, Role.FPP)).json()
    assert files["configured"] is True
    status = {f["relative_path"]: (f["status"], f["collection"], f["jumlah_chunk"]) for f in files["files"]}
    assert status["paket_siantar/BoQ.xlsx"] == ("REFERENSI", None, 0)
    assert status["rks_kb/RKS Tangki.pdf"] == ("TERINDEKS", "rks_kb", 3)

    # Sinkron kedua tanpa perubahan tidak meng-ingest ulang
    FakeStore.calls = []
    report = _sync(client)
    assert report["tidak_berubah"] == 3 and FakeStore.calls == []

    audit = query("SELECT rincian_perubahan FROM procurement_audit_trail WHERE tipe_aksi = 'SINKRON_DATASET'")
    assert audit


def test_sync_reingests_changed_and_deletes_removed(client, dataset):
    rks = _write(dataset, "rks_kb/A.pdf", b"%PDF versi 1")
    _write(dataset, "rks_kb/B.pdf")
    _sync(client)

    FakeStore.calls = []
    rks.write_bytes(b"%PDF versi 2 lebih panjang")
    (dataset / "rks_kb/B.pdf").unlink()
    report = _sync(client)
    assert report["diperbarui"] == ["rks_kb/A.pdf"]
    assert report["dihapus"] == ["rks_kb/B.pdf"]
    assert sorted(FakeStore.calls) == [("delete", "rks_kb", "B.pdf"), ("ingest", "rks_kb", "A.pdf")]


def test_sync_touch_without_content_change_is_not_reingested(client, dataset):
    path = _write(dataset, "rks_kb/A.pdf")
    _sync(client)
    FakeStore.calls = []
    stat = path.stat()
    os.utime(path, (stat.st_atime, stat.st_mtime + 60))
    report = _sync(client)
    assert report["tidak_berubah"] == 1 and FakeStore.calls == []


def test_sync_skips_duplicate_names_and_records_failures(client, dataset):
    _write(dataset, "rks_kb/2025/RKS.pdf")
    _write(dataset, "rks_kb/2026/RKS.pdf", b"%PDF lain")
    _write(dataset, "rks_kb/Rusak.pdf", b"RUSAK")
    report = _sync(client)

    assert len(report["dilewati"]) == 1 and "Nama berkas sama" in report["dilewati"][0]["alasan"]
    assert [g["berkas"] for g in report["gagal"]] == ["rks_kb/Rusak.pdf"]
    assert [c for c in FakeStore.calls if c[0] == "ingest"] == [("ingest", "rks_kb", "RKS.pdf")]

    # Setelah salah satu nama ganda dihapus, berkas yang tadinya dilewati ikut di-ingest
    skipped = report["dilewati"][0]["berkas"]
    kept = next(p for p in ("rks_kb/2025/RKS.pdf", "rks_kb/2026/RKS.pdf") if p != skipped)
    (dataset / kept).unlink()
    report = _sync(client)
    assert report["dihapus"] == [kept]
    assert skipped in report["diperbarui"]


def test_job_status_is_private_to_starter(client, dataset):
    _write(dataset, "rks_kb/A.pdf")
    headers = login(client, Role.PROCUREMENT)
    job_id = client.post("/api/dataset/sync", headers=headers).json()["id"]
    wait_job(client, headers, job_id)
    assert client.get(f"/api/jobs/{job_id}", headers=login(client, Role.FPP)).status_code == 404
    assert client.get(f"/api/jobs/{job_id}", headers=login(client, Role.ADMIN)).status_code == 200

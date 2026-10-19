"""Sinkronisasi folder dataset (drive eksternal) ke Knowledge Base Qdrant.

Modul milik tim web. Google Drive / OneDrive disinkronkan ke folder lokal oleh klien
desktop resminya (atau di-mount di server), lalu folder itu diarahkan lewat DATASET_DIR.
Modul ini hanya memanggil fungsi AI yang sudah ada (`Vector_Store.ingest_bytes` dan
`delete_source`) tanpa mengubah cara kerjanya.

Struktur folder:
    DATASET_DIR/
      rks_kb/        → di-ingest ke collection rks_kb
      contract_kb/   → di-ingest ke collection contract_kb
      amendment_kb/  → di-ingest ke collection amendment_kb
      (folder lain)  → berkas acuan saja (mis. BoQ per paket), bisa dipilih di chat
"""

import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import KB_COLLECTIONS
from app.models import DatasetFile
from app.models.enums import StatusDataset

logger = logging.getLogger(__name__)

# Ingest AI saat ini memakai PyPDFLoader, jadi hanya PDF yang bisa masuk ke collection
INGESTABLE_EXT = {".pdf"}
# Berkas yang boleh dipilih sebagai acuan di chat / ekstraksi
REFERENCE_EXT = {".pdf", ".xlsx", ".xls"}
# Berkas sementara klien sinkronisasi / Office yang harus diabaikan
_IGNORED_PREFIXES = ("~$", ".~", ".")


class DatasetUnavailableError(RuntimeError):
    """DATASET_DIR belum diatur atau foldernya tidak ditemukan."""


@dataclass
class ScannedFile:
    relative_path: str
    nama_file: str
    collection: str | None
    ukuran_bytes: int
    modified_at: datetime


@dataclass
class SyncReport:
    ditambah: list[str] = field(default_factory=list)
    diperbarui: list[str] = field(default_factory=list)
    dihapus: list[str] = field(default_factory=list)
    tidak_berubah: int = 0
    dilewati: list[dict] = field(default_factory=list)
    gagal: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "ditambah": self.ditambah,
            "diperbarui": self.diperbarui,
            "dihapus": self.dihapus,
            "tidak_berubah": self.tidak_berubah,
            "dilewati": self.dilewati,
            "gagal": self.gagal,
        }


def dataset_root(configured: Path | None) -> Path:
    if configured is None:
        raise DatasetUnavailableError("DATASET_DIR belum diatur di .env.")
    root = configured.expanduser().resolve()
    if not root.is_dir():
        raise DatasetUnavailableError(f"Folder dataset tidak ditemukan: {root}")
    return root


def scan_dataset(root: Path) -> list[ScannedFile]:
    files = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not path.is_file() or any(part.startswith(_IGNORED_PREFIXES) for part in rel.parts):
            continue
        if path.suffix.lower() not in REFERENCE_EXT:
            continue
        stat = path.stat()
        top = rel.parts[0] if len(rel.parts) > 1 else None
        files.append(
            ScannedFile(
                relative_path=rel.as_posix(),
                nama_file=path.name,
                collection=top if top in KB_COLLECTIONS else None,
                ukuran_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            )
        )
    return files


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_dataset_path(root: Path, relative_path: str) -> Path:
    """Path absolut berkas dataset; menolak path yang keluar dari DATASET_DIR."""
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise FileNotFoundError(relative_path)
    return path


async def sync_dataset(
    session: AsyncSession,
    root: Path,
    vector_store_factory: Callable[[str], object],
    on_progress: Callable[[int, int, str], None] | None = None,
) -> SyncReport:
    """Bandingkan isi folder dengan catatan di database, lalu ingest/hapus seperlunya.
    `on_progress(selesai, total, berkas)` dipanggil sebelum tiap berkas diproses."""
    report = SyncReport()
    scanned = await run_in_threadpool(scan_dataset, root)
    existing = {row.relative_path: row for row in (await session.scalars(select(DatasetFile))).all()}
    stores: dict[str, object] = {}

    def store(collection: str):
        if collection not in stores:
            stores[collection] = vector_store_factory(collection)
        return stores[collection]

    # Hapus dulu berkas yang hilang dari folder, agar namanya bisa dipakai berkas lain
    seen = {f.relative_path for f in scanned}
    for rel, row in list(existing.items()):
        if rel in seen:
            continue
        if row.status == StatusDataset.TERINDEKS and row.collection:
            try:
                await run_in_threadpool(store(row.collection).delete_source, row.nama_file)
            except Exception as e:  # noqa: BLE001 — catatan tetap dipertahankan agar bisa dicoba lagi
                report.gagal.append({"berkas": rel, "alasan": f"Gagal menghapus dari Qdrant: {e}"})
                continue
        await session.delete(row)
        del existing[rel]
        report.dihapus.append(rel)
    await session.flush()

    # Nama berkas per collection yang sudah terpakai (Vector_Store mengenali sumber dari nama berkas saja)
    names_in_use = {
        (r.collection, r.nama_file): rel for rel, r in existing.items() if r.status == StatusDataset.TERINDEKS
    }

    for i, f in enumerate(scanned):
        if on_progress:
            on_progress(i, len(scanned), f.relative_path)
        row = existing.get(f.relative_path)
        # Berkas yang dilewati/gagal selalu dievaluasi ulang (mis. setelah nama gandanya dihapus)
        settled = row is not None and row.status in (StatusDataset.TERINDEKS, StatusDataset.REFERENSI)
        if settled and row.ukuran_bytes == f.ukuran_bytes and row.modified_at == f.modified_at:
            report.tidak_berubah += 1
            continue
        path = root / f.relative_path
        digest = await run_in_threadpool(_sha256, path)
        if settled and row.hash_sha256 == digest:
            row.modified_at = f.modified_at
            report.tidak_berubah += 1
            continue

        is_new = row is None
        if is_new:
            row = DatasetFile(relative_path=f.relative_path, jumlah_chunk=0)
            session.add(row)
        row.nama_file, row.collection = f.nama_file, f.collection
        row.ukuran_bytes, row.modified_at, row.hash_sha256 = f.ukuran_bytes, f.modified_at, digest
        row.pesan, row.jumlah_chunk = None, 0

        if f.collection is None:
            row.status = StatusDataset.REFERENSI
            (report.ditambah if is_new else report.diperbarui).append(f.relative_path)
            continue

        skip_reason = None
        if path.suffix.lower() not in INGESTABLE_EXT:
            skip_reason = "Format belum didukung untuk ingest (hanya PDF)."
        elif (other := names_in_use.get((f.collection, f.nama_file), f.relative_path)) != f.relative_path:
            skip_reason = f"Nama berkas sama dengan '{other}' di collection {f.collection}. Ganti nama salah satunya."
        if skip_reason:
            row.status, row.pesan = StatusDataset.DILEWATI, skip_reason
            report.dilewati.append({"berkas": f.relative_path, "alasan": skip_reason})
            continue

        names_in_use[(f.collection, f.nama_file)] = f.relative_path
        try:
            content = await run_in_threadpool(path.read_bytes)
            row.jumlah_chunk = await run_in_threadpool(store(f.collection).ingest_bytes, content, f.nama_file)
            row.status = StatusDataset.TERINDEKS
        except Exception as e:  # satu berkas gagal tidak menghentikan berkas lain
            logger.exception("Ingest gagal: %s", f.relative_path)
            row.status, row.pesan = StatusDataset.GAGAL, str(e)[:1000]
            report.gagal.append({"berkas": f.relative_path, "alasan": row.pesan})
            await session.commit()
            continue
        (report.ditambah if is_new else report.diperbarui).append(f.relative_path)
        # Ingest bisa lama; simpan per berkas agar catatan selaras dengan Qdrant bila proses terhenti
        await session.commit()

    if on_progress:
        on_progress(len(scanned), len(scanned), "")
    await session.commit()
    return report


async def load_reference(session: AsyncSession, root: Path, file_id) -> tuple[DatasetFile, Path]:
    """Berkas dataset yang dipilih user sebagai acuan, beserta path absolutnya.
    LookupError bila tidak terdaftar atau berkasnya sudah tidak ada di folder."""
    row = await session.get(DatasetFile, file_id)
    if row is None:
        raise LookupError("Berkas dataset tidak ditemukan. Jalankan sinkronisasi ulang.")
    try:
        return row, resolve_dataset_path(root, row.relative_path)
    except FileNotFoundError as e:
        raise LookupError(f"Berkas '{row.relative_path}' sudah tidak ada di folder dataset.") from e

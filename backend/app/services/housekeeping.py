"""Pembersihan berkas sementara (masterplan 9.2), modul milik tim web.

Generator AI menulis .docx ke OUTPUT_DIR. Salinan yang menjadi milik draf disimpan di
OUTPUT_DIR/drafts dan tidak pernah dihapus di sini; berkas lain dihapus setelah
TEMP_RETENTION_DAYS hari.
"""

import asyncio
import logging
import time
from pathlib import Path

from fastapi.concurrency import run_in_threadpool

from app.config import DRAFTS_DIR, OUTPUT_DIR, settings

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 6 * 3600


def cleanup_output(output_dir: Path, keep_dir: Path, retention_days: int, now: float | None = None) -> list[Path]:
    """Hapus berkas di output_dir yang lebih tua dari retention_days, kecuali isi keep_dir."""
    if not output_dir.is_dir():
        return []
    cutoff = (now if now is not None else time.time()) - retention_days * 86400
    keep = keep_dir.resolve()
    removed = []
    for path in output_dir.rglob("*"):
        if not path.is_file() or path.resolve().is_relative_to(keep):
            continue
        if path.stat().st_mtime < cutoff:
            try:
                path.unlink()
                removed.append(path)
            except OSError:
                logger.warning("Tidak dapat menghapus berkas sementara %s", path)
    return removed


async def housekeeping_loop() -> None:
    while True:
        try:
            removed = await run_in_threadpool(cleanup_output, OUTPUT_DIR, DRAFTS_DIR, settings.temp_retention_days)
            if removed:
                logger.info("Housekeeping: %d berkas sementara dihapus", len(removed))
        except Exception:
            logger.exception("Housekeeping gagal")
        await asyncio.sleep(INTERVAL_SECONDS)

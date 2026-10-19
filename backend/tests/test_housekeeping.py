"""Pembersihan berkas sementara di OUTPUT_DIR."""

import os
import time

from app.services.housekeeping import cleanup_output


def test_cleanup_removes_old_temp_files_but_keeps_drafts(tmp_path):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    old_temp = tmp_path / "RKS_lama.docx"
    new_temp = tmp_path / "RKS_baru.docx"
    old_draft = drafts / "draf.docx"
    for path in (old_temp, new_temp, old_draft):
        path.write_bytes(b"x")
    eight_days_ago = time.time() - 8 * 86400
    for path in (old_temp, old_draft):
        os.utime(path, (eight_days_ago, eight_days_ago))

    removed = cleanup_output(tmp_path, drafts, retention_days=7)

    assert removed == [old_temp]
    assert new_temp.exists() and old_draft.exists()


def test_cleanup_ignores_missing_output_dir(tmp_path):
    assert cleanup_output(tmp_path / "tidak_ada", tmp_path / "drafts", 7) == []

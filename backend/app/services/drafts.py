"""Penyimpanan versi draf dokumen per paket (modul milik tim web).

Setiap draf baru (hasil agent atau generate dari kanvas) menjadi versi baru; hanya satu
yang aktif per paket. Berkas .docx disalin ke DRAFTS_DIR/<id draf>.docx karena generator
menulis ke nama berkas yang sama untuk judul yang sama sehingga bisa saling menimpa.
"""

import shutil
from pathlib import Path

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import DRAFTS_DIR
from app.models import DocumentDraft, TenderProject


async def active_draft(session: AsyncSession, project_id) -> DocumentDraft | None:
    return await session.scalar(
        select(DocumentDraft).where(DocumentDraft.project_id == project_id, DocumentDraft.is_active)
    )


async def add_draft_version(
    session: AsyncSession, project: TenderProject, judul: str, konten: dict, docx_src: Path | None = None
) -> DocumentDraft:
    count = await session.scalar(
        select(func.count()).select_from(DocumentDraft).where(DocumentDraft.project_id == project.id)
    )
    await session.execute(
        update(DocumentDraft)
        .where(DocumentDraft.project_id == project.id, DocumentDraft.is_active)
        .values(is_active=False)
    )
    draft = DocumentDraft(
        project_id=project.id, versi=f"v{count + 1}.0", judul_dokumen=judul[:255], konten_json=konten, is_active=True
    )
    session.add(draft)
    await session.flush()
    if docx_src is not None:
        await attach_docx(draft, docx_src)
    return draft


async def attach_docx(draft: DocumentDraft, docx_src: Path) -> None:
    target = DRAFTS_DIR / f"{draft.id}.docx"
    await run_in_threadpool(_copy, docx_src, target)
    draft.file_docx_path = str(target)


def _copy(src: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, target)


def draft_docx(draft: DocumentDraft) -> Path | None:
    """Path .docx draf bila berkasnya ada dan berada di DRAFTS_DIR."""
    if not draft.file_docx_path:
        return None
    path = Path(draft.file_docx_path).resolve()
    if not path.is_relative_to(DRAFTS_DIR.resolve()) or not path.is_file():
        return None
    return path

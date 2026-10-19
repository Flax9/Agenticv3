"""Pencatatan jejak audit append-only (masterplan 4.2 tabel 9)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditTrail
from app.models.enums import ModulTerkait, TipeAksi


async def record_audit(
    session: AsyncSession,
    *,
    tipe_aksi: TipeAksi,
    modul: ModulTerkait,
    rincian: str,
    user_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    snapshot: dict | None = None,
    ip_address: str | None = None,
    commit: bool = True,
) -> None:
    session.add(
        AuditTrail(
            tipe_aksi=tipe_aksi,
            modul_terkait=modul,
            rincian_perubahan=rincian,
            user_id=user_id,
            project_id=project_id,
            snapshot_data=snapshot,
            ip_address=ip_address,
        )
    )
    if commit:
        await session.commit()

"""Skrip seed & administrasi akun.

Contoh:
    uv run python -m app.scripts.seed admin
    uv run python -m app.scripts.seed user --username budi --email budi@contoh.id --nama "Budi" --role FPP
    uv run python -m app.scripts.seed stk data/stk_rules.json

Format berkas STK (JSON list):
    [{"nomor_aturan": "STK-01", "kategori_stk": "Jaminan", "judul_aturan": "...", "deskripsi_aturan": "...",
      "klausul_baku_docx": "...", "level_kepatuhan": "MANDATORY"}, ...]
"""

import argparse
import asyncio
import getpass
import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.core.security import hash_password
from app.database import SessionLocal, engine
from app.models import AppUser, StkRule
from app.models.enums import LevelKepatuhan, Role

MIN_PASSWORD_LENGTH = 10


async def _create_user(username: str, email: str, nama: str, role: Role, password: str, jabatan: str | None) -> bool:
    username = username.strip().lower()
    async with SessionLocal() as session:
        exists = await session.scalar(select(AppUser).where((AppUser.username == username) | (AppUser.email == email)))
        if exists:
            print(f"Lewati: username '{username}' atau email '{email}' sudah terdaftar.")
            return False
        session.add(
            AppUser(
                username=username,
                email=email,
                nama_lengkap=nama,
                jabatan=jabatan,
                role=role,
                password_hash=hash_password(password),
            )
        )
        await session.commit()
    print(f"Akun '{username}' ({role.value}) dibuat.")
    return True


async def seed_admin() -> None:
    password = settings.admin_initial_password
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"ADMIN_INITIAL_PASSWORD di .env wajib diisi (minimal {MIN_PASSWORD_LENGTH} karakter).")
    await _create_user("admin", "admin@itec.local", "Administrator Sistem", Role.ADMIN, password, None)


async def seed_user(args: argparse.Namespace) -> None:
    password = getpass.getpass("Password: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"Password minimal {MIN_PASSWORD_LENGTH} karakter.")
    if getpass.getpass("Ulangi password: ") != password:
        sys.exit("Password tidak sama.")
    await _create_user(args.username, args.email, args.nama, Role(args.role), password, args.jabatan)


async def seed_stk(path: Path) -> None:
    rows = json.loads(path.read_text(encoding="utf-8"))
    created = updated = 0
    async with SessionLocal() as session:
        for row in rows:
            rule = await session.scalar(select(StkRule).where(StkRule.nomor_aturan == row["nomor_aturan"]))
            if rule is None:
                rule = StkRule(nomor_aturan=row["nomor_aturan"])
                session.add(rule)
                created += 1
            else:
                updated += 1
            rule.kategori_stk = row["kategori_stk"]
            rule.judul_aturan = row["judul_aturan"]
            rule.deskripsi_aturan = row["deskripsi_aturan"]
            rule.klausul_baku_docx = row.get("klausul_baku_docx")
            rule.level_kepatuhan = LevelKepatuhan(row.get("level_kepatuhan", "MANDATORY"))
        await session.commit()
    print(f"Aturan STK: {created} ditambahkan, {updated} diperbarui.")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed data & administrasi akun ITeC")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("admin", help="Buat akun admin awal dari ADMIN_INITIAL_PASSWORD")
    user = sub.add_parser("user", help="Buat akun pengguna baru (password diminta interaktif)")
    user.add_argument("--username", required=True)
    user.add_argument("--email", required=True)
    user.add_argument("--nama", required=True)
    user.add_argument("--jabatan")
    user.add_argument("--role", choices=[r.value for r in Role], default=Role.FPP.value)
    stk = sub.add_parser("stk", help="Impor/perbarui katalog aturan STK dari berkas JSON")
    stk.add_argument("path", type=Path)
    args = parser.parse_args()

    try:
        if args.command == "admin":
            await seed_admin()
        elif args.command == "user":
            await seed_user(args)
        else:
            await seed_stk(args.path)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

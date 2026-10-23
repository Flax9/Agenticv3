"""Pembuat checkpointer untuk agent LangGraph (milik tim web).

Agent memakai checkpointer untuk menyimpan state percakapan per `thread_id`. `MemorySaver` bawaan
hilang saat server restart, padahal riwayat chat di database tetap ada, sehingga sesi yang sedang
menunggu BoQ atau persetujuan draf tidak bisa dilanjutkan. Di sini state disimpan di PostgreSQL
yang sama dengan aplikasi (tabel `checkpoints*` dibuat oleh `PostgresSaver.setup()`).

Memakai satu koneksi, bukan `psycopg_pool`: pool gagal start (worker thread tidak berjalan) di
lingkungan pengembangan Windows. `PostgresSaver` mengunci koneksi tunggal secara internal, jadi
aman dipakai dari threadpool; konsekuensinya akses checkpoint berjalan bergantian, yang tidak
masalah karena agent sendiri berjalan satu giliran per sesi.

Bila PostgreSQL tidak bisa dihubungi saat agent dimuat, dipakai `MemorySaver` agar aplikasi tetap
berjalan; peringatannya dicatat di log.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


def _psycopg_conninfo(database_url: str) -> str:
    """URL SQLAlchemy (postgresql+asyncpg://...) → URL libpq (postgresql://...)."""
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def make_checkpointer():
    from langgraph.checkpoint.memory import MemorySaver

    if settings.agent_checkpointer != "postgres":
        return MemorySaver()
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg import Connection
        from psycopg.rows import dict_row

        conn = Connection.connect(
            _psycopg_conninfo(settings.database_url),
            # Yang disyaratkan PostgresSaver: autocommit dan baris bertipe dict
            autocommit=True,
            prepare_threshold=0,
            row_factory=dict_row,
            connect_timeout=10,
            # Koneksi berumur panjang: keepalive mencegah diputus firewall/NAT saat idle
            keepalives=1,
            keepalives_idle=60,
        )
        saver = PostgresSaver(conn)
        # setup() menjalankan CREATE INDEX CONCURRENTLY yang menunggu semua transaksi lain selesai.
        # Tanpa batas waktu, memuat agent di dalam request (yang memegang transaksi sendiri) menunggu selamanya.
        conn.execute("SET statement_timeout = '30s'")
        saver.setup()
        conn.execute("SET statement_timeout = 0")
        return saver
    except Exception:
        logger.exception(
            "Checkpointer PostgreSQL tidak tersedia; agent memakai MemorySaver (state hilang saat restart)"
        )
        return MemorySaver()

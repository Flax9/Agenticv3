"""
contract/amendment_schema.py — Pydantic models untuk Draft Amendemen / Addendum
================================================================================
Mendefinisikan struktur Amendemen Kontrak (Addendum) yang merupakan dokumen
perubahan resmi atas Kontrak Definitif yang sudah berjalan.

Setiap Amendemen mencantumkan:
  - Referensi ke kontrak asal
  - Daftar perubahan per pasal (pasal lama vs baru + alasan)
  - Konsideran hukum (Menimbang, Mengingat, Memperhatikan)
  - Tanda tangan Para Pihak
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────────────────────

class JenisPerubahan(str, Enum):
    NILAI_KONTRAK = "Nilai Kontrak"
    WAKTU_PELAKSANAAN = "Waktu Pelaksanaan"
    LINGKUP_PEKERJAAN = "Lingkup Pekerjaan"
    PERSONEL = "Personel Inti"
    HARGA_SATUAN = "Harga Satuan / BOQ"
    SISTEM_PEMBAYARAN = "Sistem Pembayaran"
    LAINNYA = "Lainnya"


# ──────────────────────────────────────────────────────────────
# Sub-models
# ──────────────────────────────────────────────────────────────

class ItemPerubahan(BaseModel):
    """
    Satu item perubahan dalam amendemen.
    Merepresentasikan 1 pasal/klausul yang mengalami perubahan.
    """
    jenis_perubahan: JenisPerubahan
    pasal_referensi: str = Field(
        description="Nomor dan judul pasal yang diubah, e.g. 'Pasal 3 – Jangka Waktu Pelaksanaan'"
    )
    isi_lama: str = Field(
        description="Bunyi pasal / klausul SEBELUM perubahan (isi orisinal dari kontrak asal)."
    )
    isi_baru: str = Field(
        description="Bunyi pasal / klausul SETELAH perubahan (rumusan baru yang disepakati)."
    )
    alasan_perubahan: str = Field(
        description="Justifikasi / dasar hukum perubahan ini."
    )


class ReferensiKontrakAsal(BaseModel):
    """Identifikasi kontrak yang di-amend."""
    nomor_kontrak: str = ""
    judul_pekerjaan: str = ""
    tanggal_kontrak_asal: str = ""
    nama_vendor: str = ""
    nilai_kontrak_asal_str: str = ""   # Nilai sebelum perubahan (jika ada)


class KonsideranAmendemen(BaseModel):
    """
    Konsideran hukum yang wajib ada di dokumen Amendemen.
    LLM akan mengisi isi tiap bagian secara otomatis.
    """
    menimbang: List[str] = Field(
        default_factory=list,
        description="Daftar butir 'Menimbang' — alasan/latar belakang perubahan."
    )
    mengingat: List[str] = Field(
        default_factory=list,
        description="Dasar hukum / regulasi yang menjadi rujukan amendemen."
    )
    memperhatikan: List[str] = Field(
        default_factory=list,
        description="Dokumen atau fakta yang diperhatikan (berita acara, surat, dll.)."
    )


# ──────────────────────────────────────────────────────────────
# Root model: Draft Amendemen
# ──────────────────────────────────────────────────────────────

class DraftAmendemen(BaseModel):
    """
    Model lengkap Draft Amendemen / Addendum Kontrak.
    Satu dokumen ini merepresentasikan satu kali perubahan kontrak.
    """
    # ── Cover ─────────────────────────────────────────────────
    nomor_addendum: str = Field(
        description="Urutan addendum, e.g. 'Addendum Ke-1', 'Addendum Ke-2'"
    )
    tanggal_amendemen: str = ""          # Tanggal penandatanganan amendemen
    tanggal_berlaku_efektif: str = ""    # Tanggal mulai berlaku perubahan

    # ── Referensi kontrak asal ────────────────────────────────
    kontrak_asal: ReferensiKontrakAsal = Field(default_factory=ReferensiKontrakAsal)

    # ── Konsideran ────────────────────────────────────────────
    konsideran: KonsideranAmendemen = Field(default_factory=KonsideranAmendemen)

    # ── Daftar perubahan ──────────────────────────────────────
    perubahan: List[ItemPerubahan] = Field(
        default_factory=list,
        description="List of all changes. Each item corresponds to one clause being amended."
    )

    # ── Pasal Penutup (selalu ada) ────────────────────────────
    pasal_penutup: str = (
        "Ketentuan-ketentuan lain dalam Kontrak yang tidak diubah oleh Addendum ini "
        "tetap berlaku dan mengikat Para Pihak."
    )

    # ── Penandatangan ─────────────────────────────────────────
    ttd_pertamina_nama: str = ""
    ttd_pertamina_jabatan: str = ""
    ttd_vendor_nama: str = ""
    ttd_vendor_jabatan: str = "Direktur Utama"


# ──────────────────────────────────────────────────────────────
# JSON Schema string untuk LLM prompt
# ──────────────────────────────────────────────────────────────

AMENDEMEN_JSON_SCHEMA = """
{
  "nomor_addendum": "<string: e.g. 'Addendum Ke-1'>",
  "tanggal_amendemen": "<string: DD Bulan YYYY>",
  "tanggal_berlaku_efektif": "<string: DD Bulan YYYY>",
  "kontrak_asal": {
    "nomor_kontrak": "<string>",
    "judul_pekerjaan": "<string>",
    "tanggal_kontrak_asal": "<string>",
    "nama_vendor": "<string>",
    "nilai_kontrak_asal_str": "<string: e.g. Rp14.346.100.000,00>"
  },
  "konsideran": {
    "menimbang": [
      "<butir 1: alasan/latar belakang perlunya perubahan>",
      "<butir 2: ...>"
    ],
    "mengingat": [
      "Kontrak Nomor <nomor_kontrak> tanggal <tanggal>",
      "Pedoman Pengadaan Barang/Jasa PT Pertamina Patra Niaga No. A03-001/PNG200000/2024-S9",
      "<referensi hukum lain yang relevan>"
    ],
    "memperhatikan": [
      "<e.g. Berita Acara Rapat tanggal ...>",
      "<e.g. Surat Permohonan Perpanjangan No. ... dari Vendor>"
    ]
  },
  "perubahan": [
    {
      "jenis_perubahan": "<Nilai Kontrak|Waktu Pelaksanaan|Lingkup Pekerjaan|Personel Inti|Harga Satuan / BOQ|Sistem Pembayaran|Lainnya>",
      "pasal_referensi": "<e.g. Pasal 3 – Jangka Waktu Pelaksanaan>",
      "isi_lama": "<bunyi pasal/klausul SEBELUM perubahan, verbatim dari kontrak asal>",
      "isi_baru": "<bunyi pasal/klausul SETELAH perubahan, rumusan yang disepakati>",
      "alasan_perubahan": "<justifikasi perubahan ini>"
    }
  ],
  "pasal_penutup": "Ketentuan-ketentuan lain dalam Kontrak yang tidak diubah oleh Addendum ini tetap berlaku dan mengikat Para Pihak.",
  "ttd_pertamina_nama": "<string: nama pejabat penandatangan Pertamina>",
  "ttd_pertamina_jabatan": "<string: jabatan>",
  "ttd_vendor_nama": "<string: nama direktur vendor>",
  "ttd_vendor_jabatan": "Direktur Utama"
}
"""

"""
contract/schema.py — Pydantic models untuk Rancangan Kontrak Definitif
=======================================================================
Mendefinisikan struktur 20 pasal kontrak pengadaan barang/jasa
PT Pertamina Patra Niaga sesuai pedoman A03-001/PNG200000/2024-S9.

Desain:
  - Setiap Pasal adalah unit mandiri dengan nomor, judul, dan konten.
  - KontrakDefinitif adalah root model yang merangkum seluruh dokumen.
  - KONTRAK_JSON_SCHEMA adalah string schema untuk prompt LLM.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────────────────────

class JenisKontrak(str, Enum):
    LUMPSUM = "Lumpsum"
    HARGA_SATUAN = "Harga Satuan"
    GABUNGAN = "Gabungan Harga Satuan & Lumpsum"
    TERIMA_JADI = "Terima Jadi (Turnkey)"

class SistemPembayaran(str, Enum):
    MILESTONE = "Milestone"
    MONTHLY_PROGRESS = "Monthly Progress"
    TERMIN = "Termin"
    SEKALIGUS = "Sekaligus (Lumpsum)"

class TingkatRisikoCSMS(str, Enum):
    TINGGI = "Tinggi"
    SEDANG = "Sedang"
    RENDAH = "Rendah"


# ──────────────────────────────────────────────────────────────
# Sub-models: Identitas Para Pihak
# ──────────────────────────────────────────────────────────────

class PihakPertamina(BaseModel):
    """Identitas Pemberi Kerja (Pertamina)."""
    nama_perusahaan: str = "PT PERTAMINA PATRA NIAGA"
    unit_regional: str = "Regional Kalimantan"
    alamat: str = "Jln. Yos Sudarso No. 148 Balikpapan 76123"
    diwakili_oleh: str = ""          # Nama pejabat penandatangan
    jabatan: str = ""                # Jabatan pejabat penandatangan
    berdasarkan_sk: str = ""         # Nomor SK / kuasa (opsional)

class PihakVendor(BaseModel):
    """Identitas Penyedia Jasa / Vendor."""
    nama_perusahaan: str = ""
    bentuk_badan_usaha: str = "Perseroan Terbatas (PT)"
    alamat: str = ""
    npwp: str = ""
    nomor_izin_usaha: str = ""       # SIUJK / NIB / SBU
    diwakili_oleh: str = ""          # Nama Direktur / Kuasa
    jabatan: str = "Direktur Utama"


# ──────────────────────────────────────────────────────────────
# Sub-models: Nilai & Waktu
# ──────────────────────────────────────────────────────────────

class NilaiKontrak(BaseModel):
    nilai_kontrak: float = 0.0
    nilai_kontrak_str: str = "Rp0,00"
    mata_uang: str = "IDR"
    sistem_pembayaran: SistemPembayaran = SistemPembayaran.MONTHLY_PROGRESS
    retensi_persen: float = 5.0     # Persen retensi dari nilai kontrak
    uang_muka_persen: float = 0.0   # Persen uang muka (0 jika tidak ada)
    keterangan_pembayaran: str = "Pembayaran dilakukan berdasarkan progres fisik yang diverifikasi Pengawas Pekerjaan."

class JangkaWaktu(BaseModel):
    tanggal_mulai: str = ""          # Format: DD Bulan YYYY
    tanggal_selesai: str = ""
    durasi_hari_kalender: int = 180
    masa_pemeliharaan_hari: int = 90
    keterangan: str = "Jangka waktu dapat diperpanjang atas persetujuan Para Pihak yang dituangkan dalam Amendemen Kontrak."


# ──────────────────────────────────────────────────────────────
# Sub-model: Pasal (unit konten tiap pasal)
# ──────────────────────────────────────────────────────────────

class Pasal(BaseModel):
    """Satu pasal dalam kontrak."""
    nomor: int
    judul: str
    ayat: List[str] = Field(
        default_factory=list,
        description=(
            "List of clause paragraphs. Each string is one ayat (sub-clause). "
            "Use numbered sub-items within a string where needed, e.g. '1. Penyedia wajib...'"
        ),
    )


# ──────────────────────────────────────────────────────────────
# Root model: Kontrak Definitif
# ──────────────────────────────────────────────────────────────

class KontrakDefinitif(BaseModel):
    """
    Model lengkap Rancangan Kontrak Definitif Pertamina Patra Niaga.
    Mencakup identitas para pihak, nilai & waktu, dan 20 pasal.
    """
    # ── Cover / Header ────────────────────────────────────────
    judul_pekerjaan: str
    nomor_kontrak: str = "KTR-[KODE]-[TAHUN]"
    tanggal_kontrak: str = ""
    lokasi_pekerjaan: str = ""
    jenis_kontrak: JenisKontrak = JenisKontrak.GABUNGAN

    # ── Para Pihak ────────────────────────────────────────────
    pihak_pertamina: PihakPertamina = Field(default_factory=PihakPertamina)
    pihak_vendor: PihakVendor = Field(default_factory=PihakVendor)

    # ── Nilai & Waktu ─────────────────────────────────────────
    nilai_kontrak: NilaiKontrak = Field(default_factory=NilaiKontrak)
    jangka_waktu: JangkaWaktu = Field(default_factory=JangkaWaktu)

    # ── HSSE ──────────────────────────────────────────────────
    tingkat_risiko_csms: TingkatRisikoCSMS = TingkatRisikoCSMS.TINGGI

    # ── Pasal-Pasal (20 pasal wajib) ──────────────────────────
    pasal: List[Pasal] = Field(
        default_factory=list,
        description="List of 20 contract clauses (Pasal 1–20).",
    )

    # ── Lampiran (opsional) ───────────────────────────────────
    lampiran: List[str] = Field(
        default_factory=list,
        description="List of attachment titles, e.g. ['Lampiran 1: Lingkup Pekerjaan Detail', ...]",
    )


# ──────────────────────────────────────────────────────────────
# JSON Schema string untuk LLM prompt
# ──────────────────────────────────────────────────────────────

KONTRAK_JSON_SCHEMA = """
{
  "judul_pekerjaan": "<string: judul pekerjaan lengkap>",
  "nomor_kontrak": "<string: e.g. KTR-042/PND970000/2026-S7>",
  "tanggal_kontrak": "<string: e.g. 04 Desember 2025>",
  "lokasi_pekerjaan": "<string: lokasi/area kerja>",
  "jenis_kontrak": "<Lumpsum|Harga Satuan|Gabungan Harga Satuan & Lumpsum|Terima Jadi (Turnkey)>",
  "pihak_pertamina": {
    "nama_perusahaan": "PT PERTAMINA PATRA NIAGA",
    "unit_regional": "<string: e.g. Regional Kalimantan>",
    "alamat": "<string>",
    "diwakili_oleh": "<string: nama pejabat>",
    "jabatan": "<string: jabatan pejabat>",
    "berdasarkan_sk": "<string: nomor SK/kuasa, atau kosong>"
  },
  "pihak_vendor": {
    "nama_perusahaan": "<string>",
    "bentuk_badan_usaha": "<string: e.g. Perseroan Terbatas (PT)>",
    "alamat": "<string>",
    "npwp": "<string>",
    "nomor_izin_usaha": "<string: NIB/SIUJK/SBU>",
    "diwakili_oleh": "<string: nama direktur>",
    "jabatan": "<string: e.g. Direktur Utama>"
  },
  "nilai_kontrak": {
    "nilai_kontrak": <float>,
    "nilai_kontrak_str": "<string: e.g. Rp14.346.100.000,00>",
    "mata_uang": "IDR",
    "sistem_pembayaran": "<Monthly Progress|Milestone|Termin|Sekaligus (Lumpsum)>",
    "retensi_persen": <float: e.g. 5.0>,
    "uang_muka_persen": <float: e.g. 0.0>,
    "keterangan_pembayaran": "<string: detail mekanisme pembayaran>"
  },
  "jangka_waktu": {
    "tanggal_mulai": "<string: DD Bulan YYYY>",
    "tanggal_selesai": "<string: DD Bulan YYYY>",
    "durasi_hari_kalender": <int>,
    "masa_pemeliharaan_hari": <int>,
    "keterangan": "<string>"
  },
  "tingkat_risiko_csms": "<Tinggi|Sedang|Rendah>",
  "pasal": [
    {
      "nomor": 1,
      "judul": "DEFINISI DAN INTERPRETASI",
      "ayat": [
        "Dalam Kontrak ini, kecuali konteksnya menghendaki lain, istilah-istilah berikut memiliki arti sebagai berikut:",
        "1. 'Kontrak' berarti perjanjian ini beserta seluruh lampiran dan perubahannya.",
        "2. 'Pekerjaan' berarti seluruh lingkup pekerjaan sebagaimana diuraikan dalam Pasal 2.",
        "3. 'Pengawas Pekerjaan' berarti pejabat atau tim yang ditunjuk Pertamina untuk mengawasi pelaksanaan Pekerjaan.",
        "... (tambahkan definisi lain yang relevan)"
      ]
    },
    {
      "nomor": 2,
      "judul": "LINGKUP PEKERJAAN",
      "ayat": [
        "<ayat 1: uraian umum lingkup pekerjaan>",
        "<ayat 2: rincian item pekerjaan utama — buat spesifik sesuai jenis pekerjaan>",
        "<ayat 3: pekerjaan yang TIDAK termasuk dalam lingkup (exclusions)>"
      ]
    },
    {
      "nomor": 3,
      "judul": "JANGKA WAKTU PELAKSANAAN",
      "ayat": ["<isi pasal>"]
    },
    {
      "nomor": 4,
      "judul": "NILAI KONTRAK DAN PEMBAYARAN",
      "ayat": ["<isi pasal — sertakan nilai, sistem pembayaran, retensi>"]
    },
    {
      "nomor": 5,
      "judul": "HAK DAN KEWAJIBAN PARA PIHAK",
      "ayat": ["<isi pasal>"]
    },
    {
      "nomor": 6,
      "judul": "PERSONEL DAN PERALATAN",
      "ayat": ["<isi pasal>"]
    },
    {
      "nomor": 7,
      "judul": "KESELAMATAN, KESEHATAN KERJA, LINDUNGAN LINGKUNGAN (K3LL) DAN CSMS",
      "ayat": ["<isi pasal — sesuaikan dengan tingkat risiko CSMS>"]
    },
    {
      "nomor": 8,
      "judul": "SUBKONTRAKTOR",
      "ayat": ["<isi pasal>"]
    },
    {
      "nomor": 9,
      "judul": "PERUBAHAN PEKERJAAN (CHANGE ORDER)",
      "ayat": ["<isi pasal>"]
    },
    {
      "nomor": 10,
      "judul": "DENDA DAN SANKSI KETERLAMBATAN",
      "ayat": ["<isi pasal — sertakan formula denda per hari>"]
    },
    {
      "nomor": 11,
      "judul": "JAMINAN-JAMINAN",
      "ayat": ["<isi pasal: Jaminan Pelaksanaan, Pemeliharaan, TKDN>"]
    },
    {
      "nomor": 12,
      "judul": "KEADAAN KAHAR (FORCE MAJEURE)",
      "ayat": ["<isi pasal>"]
    },
    {
      "nomor": 13,
      "judul": "PENGHENTIAN DAN PEMUTUSAN KONTRAK",
      "ayat": ["<isi pasal>"]
    },
    {
      "nomor": 14,
      "judul": "PENYELESAIAN PERSELISIHAN",
      "ayat": ["<isi pasal — mediasi → arbitrase BANI>"]
    },
    {
      "nomor": 15,
      "judul": "KERAHASIAAN",
      "ayat": ["<isi pasal>"]
    },
    {
      "nomor": 16,
      "judul": "ANTI SUAP DAN INTEGRITAS",
      "ayat": ["<isi pasal — referensikan Pakta Integritas PI-07>"]
    },
    {
      "nomor": 17,
      "judul": "TINGKAT KOMPONEN DALAM NEGERI (TKDN)",
      "ayat": ["<isi pasal>"]
    },
    {
      "nomor": 18,
      "judul": "GARANSI DAN MASA PEMELIHARAAN",
      "ayat": ["<isi pasal>"]
    },
    {
      "nomor": 19,
      "judul": "SERAH TERIMA PEKERJAAN",
      "ayat": ["<isi pasal: Provisional Hand Over (PHO) dan Final Hand Over (FHO)>"]
    },
    {
      "nomor": 20,
      "judul": "KETENTUAN LAIN-LAIN",
      "ayat": [
        "<ayat 1: amendemen harus tertulis dan ditandatangani Para Pihak>",
        "<ayat 2: hukum yang berlaku — hukum Republik Indonesia>",
        "<ayat 3: korespondensi resmi>",
        "<ayat 4: ketentuan lain yang relevan>"
      ]
    }
  ],
  "lampiran": [
    "Lampiran 1: Lingkup dan Spesifikasi Teknis Pekerjaan",
    "Lampiran 2: Daftar Harga Satuan / Bill of Quantity",
    "Lampiran 3: Jadwal Pelaksanaan Pekerjaan",
    "Lampiran 4: Daftar Personel Inti",
    "Lampiran 5: Daftar Peralatan Utama"
  ]
}
"""

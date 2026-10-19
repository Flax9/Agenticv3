"""Domain nilai terkontrol (masterplan 4.2 & 4.3). Dipakai bersama oleh model dan schema Pydantic."""

from enum import Enum


class Role(str, Enum):
    ADMIN = "ADMIN"
    PROCUREMENT = "PROCUREMENT"
    FPP = "FPP"
    APPROVER = "APPROVER"
    AUDITOR = "AUDITOR"


class TipeDokumen(str, Enum):
    TENDER = "tender"
    RKS = "rks"
    KONTRAK = "kontrak"
    AMENDEMEN = "amendemen"


class ResikoCsms(str, Enum):
    EKSTRIM = "Ekstrim"
    TINGGI = "Tinggi"
    SEDANG = "Sedang"
    RENDAH = "Rendah"


class StatusTahap(str, Enum):
    DRAFT = "DRAFT"
    EKSTRAKSI = "EKSTRAKSI"
    REVIEW_CANVAS = "REVIEW_CANVAS"
    PUBLISHED = "PUBLISHED"


class StatusApproval(str, Enum):
    DRAFT = "DRAFT"
    MENUNGGU_REVIEW = "MENUNGGU_REVIEW"
    DISETUJUI = "DISETUJUI"
    DITOLAK = "DITOLAK"


class StatusVerifikasi(str, Enum):
    BELUM_DICEK = "BELUM_DICEK"
    COMPLIANT = "COMPLIANT"
    WARNING = "WARNING"
    DEVIATED = "DEVIATED"


class TipeBerkas(str, Enum):
    BOQ_EXCEL = "BOQ_EXCEL"
    BOQ_PDF = "BOQ_PDF"
    RKS_PDF = "RKS_PDF"
    TOR_KAK = "TOR_KAK"
    GAMBAR_TEKNIK = "GAMBAR_TEKNIK"


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class LevelKepatuhan(str, Enum):
    MANDATORY = "MANDATORY"
    OPTIONAL = "OPTIONAL"


class TipeAksi(str, Enum):
    LOGIN = "LOGIN"
    LOGIN_GAGAL = "LOGIN_GAGAL"
    UPLOAD_BOQ = "UPLOAD_BOQ"
    EKSTRAKSI = "EKSTRAKSI"
    GENERATE_DOCX = "GENERATE_DOCX"
    REVISI_PASAL = "REVISI_PASAL"
    APPROVAL = "APPROVAL"
    EXPORT_DOKUMEN = "EXPORT_DOKUMEN"
    HAPUS_PROYEK = "HAPUS_PROYEK"
    KB_INGEST = "KB_INGEST"
    KB_HAPUS = "KB_HAPUS"
    KELOLA_USER = "KELOLA_USER"


class ModulTerkait(str, Enum):
    CANVAS = "CANVAS"
    CHAT = "CHAT"
    EXPORTER = "EXPORTER"
    AUTH = "AUTH"
    KNOWLEDGE_BASE = "KNOWLEDGE_BASE"

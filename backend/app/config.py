"""Konfigurasi aplikasi dari environment variable / berkas .env.

Berkas `.env` dibaca dari root proyek (agenticv3/.env). Modul AI hasil porting dari
Agentic_Rag_Pertamina_camp masih membaca sebagian nilai via os.getenv(), sehingga
.env juga dimuat ke os.environ di sini.
"""

from pathlib import Path

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    debug: bool = False
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # LLM (OpenRouter)
    openrouter_api_key: str = ""
    llm_model_name: str = "qwen/qwen3-7b-flash"  # nilai asli config camp (dipakai modul contract)

    # Qdrant (dev: Qdrant Cloud; produksi: container qdrant)
    qdrant_cluster_endpoint: str = ""
    qdrant_api_key: str = ""
    embedding_model: str = "sentence-transformers/all-minilm-l6-v2"

    # Penyimpanan berkas
    output_dir: Path = PROJECT_ROOT / "output"
    max_upload_mb: int = 100
    # Berkas sementara di OUTPUT_DIR (di luar folder drafts/) dihapus setelah sekian hari
    temp_retention_days: int = 7
    housekeeping_enabled: bool = True

    # Folder dataset yang disinkronkan dari Google Drive / OneDrive (klien desktop atau mount).
    # Subfolder rks_kb/, contract_kb/, amendment_kb/ di-ingest ke Qdrant; folder lain hanya berkas acuan.
    dataset_dir: Path | None = None

    @field_validator("dataset_dir", mode="before")
    @classmethod
    def _empty_dataset_dir(cls, value):
        # "DATASET_DIR=" kosong berarti belum diatur, bukan direktori kerja saat ini
        return None if isinstance(value, str) and not value.strip() else value

    # Database (PostgreSQL via asyncpg)
    database_url: str = "postgresql+asyncpg://pertamina_user:pertamina_dev@localhost:5432/pertamina_db"

    # Autentikasi
    jwt_secret: str = ""
    jwt_access_ttl_minutes: int = 30
    jwt_refresh_ttl_days: int = 7
    # Cookie refresh token hanya dikirim lewat HTTPS; matikan khusus development lokal (http)
    cookie_secure: bool = True
    login_max_failures: int = 5
    login_lockout_minutes: int = 15
    admin_initial_password: str = ""


settings = Settings()

ASSETS_DIR = BACKEND_DIR / "assets"
OUTPUT_DIR = settings.output_dir
# Salinan .docx milik draf (tidak ikut dibersihkan otomatis)
DRAFTS_DIR = OUTPUT_DIR / "drafts"

# Konstanta yang dipakai modul AI hasil porting (nama dipertahankan agar import tetap sama)
EMBEDDING_MODEL = settings.embedding_model
LLM_MODEL_NAME = settings.llm_model_name
COLLECTION_RKS = "rks_kb"
COLLECTION_CONTRACT = "contract_kb"
COLLECTION_AMENDMENT = "amendment_kb"
VECTOR_SIZE = 384  # dimensi all-minilm-l6-v2

KB_COLLECTIONS = {
    "rks_kb": COLLECTION_RKS,
    "contract_kb": COLLECTION_CONTRACT,
    "amendment_kb": COLLECTION_AMENDMENT,
}

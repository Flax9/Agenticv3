# Image backend FastAPI (masterplan 8.2). Dependensi dipasang dari pyproject.toml + uv.lock,
# sama persis dengan lingkungan development. Di Linux torch memakai build CPU (lihat pyproject).

# Stage 1: pasang dependensi dengan uv ke virtualenv /app/.venv
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

# Stage 2: runtime
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PATH="/app/.venv/bin:$PATH" \
    OUTPUT_DIR=/app/output \
    HF_HOME=/app/.cache/huggingface

# curl untuk healthcheck; libglib/libgl dibutuhkan OpenCV yang dipakai Docling
RUN apt-get update && apt-get install -y --no-install-recommends curl libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Akun non-root
RUN groupadd -r pertamina && useradd -r -g pertamina -d /app pertamina

COPY --from=builder /app/.venv /app/.venv
COPY --chown=pertamina:pertamina . .
# Buang CRLF bila repo di-checkout di Windows, agar shebang tetap valid
RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh \
    && mkdir -p /app/output /app/.cache && chown -R pertamina:pertamina /app/output /app/.cache

USER pertamina
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD curl -fs http://localhost:8000/api/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
# Satu worker: job latar belakang, lock per sesi, rate limit login, dan state agent (MemorySaver)
# disimpan di memori proses. Tambah worker hanya setelah semuanya dipindah ke Redis/Postgres.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]

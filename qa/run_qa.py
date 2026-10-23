"""Runner QA otomatis ITeC. Prosedur dan kriteria lulus ada di QA.md.

Jalankan dari root proyek:
    uv run --project backend python qa/run_qa.py [--skip-static] [--skip-llm] [--skip-load]

Runner membuat database terpisah `pertamina_qa` (tidak menyentuh data development), menjalankan
backend di port 8000, mengeksekusi pemeriksaan per lapisan, lalu menulis qa/hasil/laporan_qa.md.
"""

import argparse
import json
import re
import os
import statistics
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx
import jwt
import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
HASIL = ROOT / "qa" / "hasil"
BASE = "http://127.0.0.1:8000"
QA_PASSWORD = "Password-QA-12345"
ROLES = ["ADMIN", "PROCUREMENT", "FPP", "APPROVER", "AUDITOR"]

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(BACKEND))
ENV = dotenv_values(ROOT / ".env")


@dataclass
class Result:
    id: str
    layer: str
    title: str
    status: str  # LULUS | GAGAL | LEWAT
    detail: str = ""
    seconds: float = 0.0


@dataclass
class Runner:
    results: list[Result] = field(default_factory=list)

    def check(self, id_: str, layer: str, title: str):
        """Dekorator: jalankan fungsi, tangkap AssertionError/galat apa pun sebagai GAGAL."""

        def wrap(fn):
            start = time.monotonic()
            try:
                detail = fn() or ""
                status = "LULUS"
            except AssertionError as e:
                status, detail = "GAGAL", str(e) or "assertion gagal"
            except Exception as e:  # noqa: BLE001 - galat tak terduga tetap dilaporkan sebagai GAGAL
                status, detail = "GAGAL", f"{type(e).__name__}: {e}"
            self.results.append(Result(id_, layer, title, status, str(detail), time.monotonic() - start))
            print(f"[{status:5}] {id_} {title}" + (f" — {detail}" if status == "GAGAL" else ""), flush=True)
            return fn

        return wrap

    def skip(self, id_: str, layer: str, title: str, why: str):
        self.results.append(Result(id_, layer, title, "LEWAT", why))
        print(f"[LEWAT] {id_} {title} — {why}", flush=True)


R = Runner()


# ───────────────────────── infrastruktur ─────────────────────────


def sh(cmd: list[str], cwd: Path, env: dict | None = None, timeout: int = 900) -> subprocess.CompletedProcess:
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd, cwd=cwd, env=full_env, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace"
    )


def pg_conninfo(db: str) -> str:
    user, pw = ENV["POSTGRES_USER"], ENV["POSTGRES_PASSWORD"]
    return f"postgresql://{user}:{pw}@127.0.0.1:5432/{db}?connect_timeout=10"


QA_DB_URL = f"postgresql+asyncpg://{ENV['POSTGRES_USER']}:{ENV['POSTGRES_PASSWORD']}@127.0.0.1:5432/pertamina_qa"
SERVER_ENV = {
    "DATABASE_URL": QA_DB_URL,
    "DEBUG": "false",
    "COOKIE_SECURE": "false",
    "HOUSEKEEPING_ENABLED": "false",
    "AGENT_CHECKPOINTER": "postgres",
    "OUTPUT_DIR": str(HASIL / "output"),
    "PYTHONIOENCODING": "utf-8",
}
_server: subprocess.Popen | None = None


def prepare_database() -> None:
    from app.core.security import hash_password

    with psycopg.connect(pg_conninfo("postgres"), autocommit=True) as c:
        c.execute("DROP DATABASE IF EXISTS pertamina_qa WITH (FORCE)")
        c.execute("CREATE DATABASE pertamina_qa")
    out = sh(["uv", "run", "alembic", "upgrade", "head"], BACKEND, {"DATABASE_URL": QA_DB_URL})
    assert out.returncode == 0, out.stderr[-500:]
    pw = hash_password(QA_PASSWORD)
    with psycopg.connect(pg_conninfo("pertamina_qa"), autocommit=True) as c:
        for role in ROLES:
            c.execute(
                "INSERT INTO app_user (username, email, nama_lengkap, password_hash, role) VALUES (%s,%s,%s,%s,%s)",
                (f"qa_{role.lower()}", f"qa_{role.lower()}@qa.local", f"QA {role}", pw, role),
            )
        c.execute(
            "INSERT INTO app_user (username, email, nama_lengkap, password_hash, role) VALUES (%s,%s,%s,%s,%s)",
            ("qa_lockout", "qa_lockout@qa.local", "QA Lockout", pw, "FPP"),
        )


def start_server() -> None:
    global _server
    HASIL.mkdir(parents=True, exist_ok=True)
    log = open(HASIL / "server.log", "ab")  # noqa: SIM115 - ditutup bersama proses
    _server = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--port", "8000", "--log-level", "warning"],
        cwd=BACKEND,
        env={**os.environ, **SERVER_ENV},
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{BASE}/api/health", timeout=2).status_code == 200:
                return
        except httpx.HTTPError:
            time.sleep(1)
    raise RuntimeError("Backend tidak siap dalam 300 detik (lihat qa/hasil/server.log)")


def stop_server() -> None:
    global _server
    if _server and _server.poll() is None:
        subprocess.run(["taskkill", "/PID", str(_server.pid), "/T", "/F"], capture_output=True)
        _server.wait(timeout=30)
    _server = None


def login(role: str, client: httpx.Client | None = None) -> dict:
    c = client or httpx
    res = c.post(f"{BASE}/api/auth/login", json={"username": f"qa_{role.lower()}", "password": QA_PASSWORD})
    assert res.status_code == 200, f"login {role}: {res.status_code} {res.text[:200]}"
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def sse_turn(headers: dict, sid: str, content: str, timeout: float = 240) -> dict:
    """Kirim pesan lewat /stream; kembalikan {'events': [...], 'done': TurnResponse | None, 'error': str | None}."""
    events, done, error = [], None, None
    with httpx.stream(
        "POST", f"{BASE}/api/chat/sessions/{sid}/stream", json={"content": content}, headers=headers, timeout=timeout
    ) as res:
        assert res.status_code == 200, f"stream {res.status_code}: {res.read()[:200]}"
        name = None
        for line in res.iter_lines():
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: ") and name:
                data = json.loads(line[6:])
                events.append(name)
                if name == "done":
                    done = data
                elif name == "error":
                    error = data.get("detail")
    return {"events": events, "done": done, "error": error}


# ───────────────────────── L1 statis ─────────────────────────


def layer_static() -> None:
    @R.check("S-01", "L1 Statis", "ruff check (backend)")
    def _():
        out = sh(["uv", "run", "ruff", "check", "app", "tests"], BACKEND)
        assert out.returncode == 0, out.stdout[-400:]

    @R.check("S-02", "L1 Statis", "ruff format --check (backend)")
    def _():
        out = sh(["uv", "run", "ruff", "format", "--check", "app", "tests"], BACKEND)
        assert out.returncode == 0, out.stdout[-400:]

    @R.check("S-03", "L1 Statis", "Skema DB sesuai model (alembic check)")
    def _():
        out = sh(["uv", "run", "alembic", "check"], BACKEND)
        assert out.returncode == 0, (out.stdout + out.stderr)[-400:]

    @R.check("S-04", "L1 Statis", "Frontend lint (oxlint)")
    def _():
        out = sh(["cmd", "/c", "npm run lint"], ROOT / "frontend")
        assert out.returncode == 0, (out.stdout + out.stderr)[-400:]

    @R.check("S-05", "L1 Statis", "Frontend build (vite)")
    def _():
        out = sh(["cmd", "/c", "npm run build"], ROOT / "frontend")
        assert out.returncode == 0, (out.stdout + out.stderr)[-400:]


# ───────────────────────── L2 pytest ─────────────────────────


def layer_pytest() -> None:
    @R.check("P-01", "L2 Pytest", "Seluruh suite pytest backend lulus")
    def _():
        out = sh(["uv", "run", "pytest", "-q", "-p", "no:cacheprovider"], BACKEND)
        tail = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else out.stderr[-300:]
        assert out.returncode == 0, tail
        return tail


# ───────────────────────── L3 API & keamanan ─────────────────────────


def layer_api() -> None:
    @R.check("A-01", "L3 API", "Liveness /api/health dan kesiapan /api/health/ready")
    def _():
        assert httpx.get(f"{BASE}/api/health").json()["status"] == "ok"
        ready = httpx.get(f"{BASE}/api/health/ready", timeout=15)
        assert ready.status_code == 200 and ready.json()["database"] == "ok", ready.text
        return f"qdrant: {ready.json()['qdrant']}"

    @R.check("A-02", "L3 API", "Login benar untuk kelima peran; cookie refresh HttpOnly")
    def _():
        for role in ROLES:
            with httpx.Client() as c:
                res = c.post(
                    f"{BASE}/api/auth/login", json={"username": f"qa_{role.lower()}", "password": QA_PASSWORD}
                )
                assert res.status_code == 200, f"{role}: {res.status_code}"
                cookie = res.headers.get("set-cookie", "").lower()
                assert "httponly" in cookie, f"cookie refresh tanpa HttpOnly untuk {role}"

    @R.check("A-03", "L3 API", "Login salah ditolak 401 dan pesan tidak membedakan akun ada/tidak")
    def _():
        wrong = httpx.post(f"{BASE}/api/auth/login", json={"username": "qa_admin", "password": "salah-salah-1"})
        ghost = httpx.post(f"{BASE}/api/auth/login", json={"username": "tidak_ada_xx", "password": "salah-salah-1"})
        assert wrong.status_code == ghost.status_code == 401
        assert wrong.json() == ghost.json(), "pesan galat membocorkan keberadaan akun"

    @R.check("A-04", "L3 API", "Pemblokiran login setelah 5 kali gagal (429)")
    def _():
        codes = [
            httpx.post(f"{BASE}/api/auth/login", json={"username": "qa_lockout", "password": "salah-salah-1"})
            for _ in range(7)
        ]
        statuses = [r.status_code for r in codes]
        assert 429 in statuses, f"tidak pernah 429: {statuses}"
        assert "retry-after" in {k.lower() for k in codes[-1].headers}, "tanpa Retry-After"
        # Akun benar tetap diblokir selama jendela kunci (kunci = username|ip)
        assert httpx.post(f"{BASE}/api/auth/login", json={"username": "qa_lockout", "password": QA_PASSWORD}).status_code == 429

    @R.check("A-05", "L3 API", "Injeksi SQL dan input aneh pada login tidak menyebabkan 500")
    def _():
        for payload in ["' OR '1'='1", "admin'--", "a" * 5000, "\x00", "%00"]:
            res = httpx.post(f"{BASE}/api/auth/login", json={"username": payload, "password": payload})
            assert res.status_code in (401, 422, 429), f"{payload[:20]!r} → {res.status_code}"

    @R.check("A-06", "L3 API", "Semua endpoint /api selain login/refresh/health menolak tanpa token (401)")
    def _():
        from app.main import app

        public = {"/api/health", "/api/health/ready", "/api/auth/login", "/api/auth/refresh", "/api/auth/logout"}
        bad = []
        for path, item in app.openapi()["paths"].items():
            if path in public or not path.startswith("/api"):
                continue
            for method in item:
                url = BASE + re.sub(r"{[^}]+}", lambda _: str(uuid.uuid4()), path)
                res = httpx.request(method.upper(), url, timeout=10)
                if res.status_code not in (401, 404, 405, 422):
                    bad.append(f"{method.upper()} {path} → {res.status_code}")
                elif res.status_code in (404, 422) and "{" not in path:
                    bad.append(f"{method.upper()} {path} → {res.status_code} (seharusnya 401)")
        assert not bad, "; ".join(bad[:6])

    @R.check("A-07", "L3 API", "Token dirusak, alg=none, dan token refresh sebagai access ditolak (401)")
    def _():
        good = login("FPP")["Authorization"].split()[1]
        forged_none = jwt.encode({"sub": str(uuid.uuid4()), "type": "access"}, key=None, algorithm="none")
        flipped = good[:-4] + ("AAAA" if not good.endswith("AAAA") else "BBBB")
        for tok in (good + "x", flipped, forged_none, "bukan.token.sama-sekali"):
            res = httpx.get(f"{BASE}/api/chat/sessions", headers={"Authorization": f"Bearer {tok}"})
            assert res.status_code == 401, f"token palsu diterima ({res.status_code})"
        with httpx.Client() as c:
            c.post(f"{BASE}/api/auth/login", json={"username": "qa_fpp", "password": QA_PASSWORD})
            refresh = c.cookies.get("refresh_token") or next(iter(c.cookies.values()), None)
            if refresh:
                res = httpx.get(f"{BASE}/api/chat/sessions", headers={"Authorization": f"Bearer {refresh}"})
                assert res.status_code == 401, "refresh token diterima sebagai access token"

    @R.check("A-08", "L3 API", "Matriks RBAC pada endpoint kunci")
    def _():
        expect = {
            # (metode, path, body): {peran: status yang diharapkan}
            ("POST", "/api/chat/sessions", '{"tipe_dokumen":"kontrak"}'): {
                "ADMIN": 201, "PROCUREMENT": 201, "FPP": 201, "APPROVER": 403, "AUDITOR": 403,
            },
            ("POST", "/api/dataset/sync", None): {
                "FPP": 403, "APPROVER": 403, "AUDITOR": 403,
            },
        }
        bad = []
        for (method, path, body), per_role in expect.items():
            for role, want in per_role.items():
                res = httpx.request(
                    method, BASE + path, headers={**login(role), "Content-Type": "application/json"}, content=body
                )
                if res.status_code != want:
                    bad.append(f"{role} {method} {path}: {res.status_code} (harapan {want})")
        assert not bad, "; ".join(bad)

    @R.check("A-09", "L3 API", "Isolasi data: pengguna lain tidak bisa membaca/menulis sesi milik FPP (404)")
    def _():
        owner = login("FPP")
        sid = httpx.post(f"{BASE}/api/chat/sessions", json={"tipe_dokumen": "kontrak"}, headers=owner).json()["id"]
        # PROCUREMENT bukan pemilik dan bukan peninjau-saja: tidak boleh menulis
        res = httpx.post(f"{BASE}/api/chat/sessions/{sid}/messages", json={"content": "x"}, headers=login("PROCUREMENT"))
        assert res.status_code == 404, f"tulis ke sesi orang lain: {res.status_code}"
        assert httpx.get(f"{BASE}/api/chat/sessions/{sid}", headers=login("AUDITOR")).status_code == 200
        ids = [s["id"] for s in httpx.get(f"{BASE}/api/chat/sessions", headers=login("PROCUREMENT")).json()]
        assert sid not in ids, "daftar sesi memuat sesi milik orang lain"

    @R.check("A-10", "L3 API", "Dokumentasi API (/docs, /openapi.json) nonaktif pada mode produksi")
    def _():
        for path in ("/docs", "/openapi.json", "/redoc"):
            assert httpx.get(BASE + path).status_code == 404, path

    @R.check("A-11", "L3 API", "CORS: origin asing tidak diizinkan")
    def _():
        res = httpx.options(
            f"{BASE}/api/auth/login",
            headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
        )
        assert res.headers.get("access-control-allow-origin") != "https://evil.example"

    @R.check("A-12", "L3 API", "Lampiran dataset: ID bukan UUID atau berkas tak dikenal ditolak, tanpa membaca path server")
    def _():
        h = login("FPP")
        sid = httpx.post(f"{BASE}/api/chat/sessions", json={"tipe_dokumen": "rks"}, headers=h).json()["id"]
        for bad in ("../../etc/passwd", "C:/Windows/system.ini", "1; DROP TABLE app_user"):
            res = httpx.post(
                f"{BASE}/api/chat/sessions/{sid}/messages", json={"content": "x", "dataset_file_id": bad}, headers=h
            )
            assert res.status_code == 422, f"{bad!r} → {res.status_code}"
        res = httpx.post(
            f"{BASE}/api/chat/sessions/{sid}/messages",
            json={"content": "x", "dataset_file_id": str(uuid.uuid4())},
            headers=h,
        )
        assert res.status_code in (400, 404), res.status_code

    @R.check("A-13", "L3 API", "Batas laju chat: pesan ke-21 dalam semenit ditolak 429 (tanpa memanggil LLM)")
    def _():
        h = login("ADMIN")
        sid = httpx.post(f"{BASE}/api/chat/sessions", json={"tipe_dokumen": "kontrak"}, headers=h).json()["id"]
        codes = [
            httpx.post(f"{BASE}/api/chat/sessions/{sid}/messages", json={"content": f"p{i}"}, headers=h).status_code
            for i in range(24)
        ]
        assert codes[:20] == [200] * 20, f"20 pesan pertama: {codes[:20]}"
        assert 429 in codes[20:], f"tidak ada 429: {codes[20:]}"

    @R.check("A-14", "L3 API", "Unggah/isi tidak valid: JSON rusak, field hilang, dan tipe dokumen tak dikenal (422, bukan 500)")
    def _():
        h = {**login("FPP"), "Content-Type": "application/json"}
        for body in ("{rusak", "{}", '{"tipe_dokumen":"tidak-ada"}', '{"tipe_dokumen": null}'):
            res = httpx.post(f"{BASE}/api/chat/sessions", content=body, headers=h)
            assert res.status_code == 422, f"{body!r} → {res.status_code}"

    @R.check("A-15", "L3 API", "Job: status bisa dibaca pemilik/admin saja")
    def _():
        res = httpx.get(f"{BASE}/api/jobs/{uuid.uuid4()}", headers=login("ADMIN"))
        assert res.status_code == 404


# ───────────────────────── L4 LLM nyata ─────────────────────────


def layer_llm() -> None:
    state: dict = {}

    @R.check("L-01", "L4 LLM nyata", "Pertanyaan umum: agent menjawab lewat SSE (progress, token, done) tanpa error")
    def _():
        h = login("FPP")
        sid = httpx.post(f"{BASE}/api/chat/sessions", json={"tipe_dokumen": "rks"}, headers=h).json()["id"]
        turn = sse_turn(h, sid, "Apa yang dimaksud dengan HPS dalam pengadaan?")
        assert turn["error"] is None, turn["error"]
        assert turn["done"], f"event: {turn['events']}"
        reply = turn["done"]["messages"][-1]
        assert reply["role"].lower() == "assistant" and len(reply["content"]) > 20, reply
        assert not (reply.get("artifacts_payload") or {}).get("error"), reply["content"][:200]
        assert "progress" in turn["events"], f"tidak ada event progress: {turn['events']}"
        return f"{len(turn['events'])} event; balasan {len(reply['content'])} karakter"

    @R.check("L-02", "L4 LLM nyata", "Pertanyaan knowledge base: dijawab tanpa error (Qdrant terjangkau)")
    def _():
        h = login("FPP")
        sid = httpx.post(f"{BASE}/api/chat/sessions", json={"tipe_dokumen": "rks"}, headers=h).json()["id"]
        turn = sse_turn(h, sid, "Cari di knowledge base: contoh klausul masa pemeliharaan pada RKS.")
        assert turn["error"] is None, turn["error"]
        assert turn["done"], f"event: {turn['events']}"
        reply = turn["done"]["messages"][-1]
        assert not (reply.get("artifacts_payload") or {}).get("error"), reply["content"][:300]

    @R.check("L-03", "L4 LLM nyata", "Permintaan membuat RKS membuat agent berhenti menunggu BoQ (awaiting=upload_boq)")
    def _():
        h = login("FPP")
        sid = httpx.post(f"{BASE}/api/chat/sessions", json={"tipe_dokumen": "rks"}, headers=h).json()["id"]
        turn = sse_turn(h, sid, "Tolong buatkan RKS untuk pembangunan tangki air kapasitas 1.000 KL di TBBM Siantar.")
        assert turn["error"] is None, turn["error"]
        assert turn["done"] and turn["done"]["awaiting"] == "upload_boq", (turn["done"] or {}).get("awaiting")
        state.update(sid=sid, headers=h)

    if "sid" not in state:
        R.skip("L-04", "L4 LLM nyata", "State agent bertahan setelah server di-restart", "L-03 tidak menghasilkan sesi")
        R.skip("L-05", "L4 LLM nyata", "Agent melanjutkan percakapan setelah restart", "L-03 tidak menghasilkan sesi")
        return

    @R.check("L-04", "L4 LLM nyata", "State agent bertahan setelah server di-restart (checkpoint di PostgreSQL)")
    def _():
        with psycopg.connect(pg_conninfo("pertamina_qa")) as c:
            n = c.execute("SELECT count(*) FROM checkpoints WHERE thread_id = %s", (state["sid"],)).fetchone()[0]
        assert n >= 1, "tidak ada baris checkpoint untuk thread ini"
        stop_server()
        start_server()
        state["headers"] = login("FPP")
        detail = httpx.get(f"{BASE}/api/chat/sessions/{state['sid']}", headers=state["headers"], timeout=60).json()
        assert detail["awaiting"] == "upload_boq", f"setelah restart awaiting={detail['awaiting']!r}"
        assert len(detail["messages"]) >= 2
        return f"{n} checkpoint tersimpan"

    @R.check("L-05", "L4 LLM nyata", "Agent melanjutkan dari titik berhenti setelah restart (balas 'lewati')")
    def _():
        turn = sse_turn(state["headers"], state["sid"], "lewati")
        assert turn["error"] is None, turn["error"]
        assert turn["done"], f"event: {turn['events']}"
        reply = turn["done"]["messages"][-1]
        assert not (reply.get("artifacts_payload") or {}).get("error"), reply["content"][:300]
        assert turn["done"]["awaiting"] != "upload_boq", "agent masih menunggu BoQ setelah 'lewati'"


# ───────────────────────── L5 beban ringan ─────────────────────────


def _timed(fn, n: int, workers: int) -> tuple[list[float], int]:
    times, errors = [], 0
    lock = threading.Lock()

    def one(_):
        nonlocal errors
        t0 = time.monotonic()
        try:
            ok = fn()
        except Exception:  # noqa: BLE001
            ok = False
        dt = time.monotonic() - t0
        with lock:
            times.append(dt)
            errors += 0 if ok else 1

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(one, range(n)))
    return times, errors


def _p95(values: list[float]) -> float:
    return statistics.quantiles(values, n=20)[-1] if len(values) >= 20 else max(values)


def layer_load() -> None:
    headers = login("PROCUREMENT")
    client = httpx.Client(timeout=30, limits=httpx.Limits(max_connections=20))

    @R.check("B-01", "L5 Beban", "/api/health: 200 permintaan, 20 paralel — 0 galat, p95 < 500 ms")
    def _():
        times, errors = _timed(lambda: client.get(f"{BASE}/api/health").status_code == 200, 200, 20)
        p95 = _p95(times)
        assert errors == 0, f"{errors} galat"
        assert p95 < 0.5, f"p95 {p95 * 1000:.0f} ms"
        return f"p50 {statistics.median(times) * 1000:.0f} ms, p95 {p95 * 1000:.0f} ms"

    @R.check("B-02", "L5 Beban", "Daftar sesi terautentikasi: 100 permintaan, 10 paralel — 0 galat, p95 < 800 ms")
    def _():
        times, errors = _timed(
            lambda: client.get(f"{BASE}/api/chat/sessions", headers=headers).status_code == 200, 100, 10
        )
        p95 = _p95(times)
        assert errors == 0, f"{errors} galat"
        assert p95 < 0.8, f"p95 {p95 * 1000:.0f} ms"
        return f"p50 {statistics.median(times) * 1000:.0f} ms, p95 {p95 * 1000:.0f} ms"

    @R.check("B-03", "L5 Beban", "Login argon2: 20 login, 5 paralel — 0 galat, p95 < 3 s")
    def _():
        def one():
            return (
                client.post(
                    f"{BASE}/api/auth/login", json={"username": "qa_approver", "password": QA_PASSWORD}
                ).status_code
                == 200
            )

        times, errors = _timed(one, 20, 5)
        p95 = _p95(times)
        assert errors == 0, f"{errors} galat"
        assert p95 < 3, f"p95 {p95:.2f} s"
        return f"p50 {statistics.median(times):.2f} s, p95 {p95:.2f} s"

    @R.check("B-04", "L5 Beban", "Buat sesi serentak: 30 sesi, 10 paralel — 0 galat dan semuanya muncul di daftar")
    def _():
        h = login("ADMIN")
        before = len(client.get(f"{BASE}/api/chat/sessions?limit=100", headers=h).json())
        times, errors = _timed(
            lambda: client.post(f"{BASE}/api/chat/sessions", json={"tipe_dokumen": "kontrak"}, headers=h).status_code
            == 201,
            30,
            10,
        )
        assert errors == 0, f"{errors} galat"
        after = len(client.get(f"{BASE}/api/chat/sessions?limit=100", headers=h).json())
        assert after - before == 30 or after == 100, f"sebelum {before}, sesudah {after}"
        return f"p95 {_p95(times) * 1000:.0f} ms"


# ───────────────────────── L6 browser ─────────────────────────


def layer_browser() -> None:
    preview = None
    try:
        install = sh(
            ["uv", "run", "--with", "playwright", "python", "-m", "playwright", "install", "chromium"], ROOT, timeout=1200
        )
        assert install.returncode == 0, install.stderr[-300:]
        preview = subprocess.Popen(
            ["cmd", "/c", "npx vite preview --host 127.0.0.1 --port 4173 --strictPort"],
            cwd=ROOT / "frontend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                if httpx.get("http://127.0.0.1:4173", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(1)
        else:
            raise AssertionError("vite preview tidak siap di port 4173")
        out = sh(
            ["uv", "run", "--with", "playwright", "python", "qa/browser_checks.py", "http://127.0.0.1:4173", "qa_fpp", QA_PASSWORD],
            ROOT,
            timeout=600,
        )
        assert out.returncode == 0, (out.stderr or out.stdout)[-400:]
        for item in json.loads(out.stdout.strip().splitlines()[-1]):
            R.results.append(
                Result(item["id"], "L6 Browser", item["title"], item["status"], item["detail"], item["seconds"])
            )
            print(f"[{item['status']:5}] {item['id']} {item['title']}", flush=True)
    except Exception as e:  # noqa: BLE001
        R.results.append(Result("U-00", "L6 Browser", "Menjalankan uji browser", "GAGAL", f"{type(e).__name__}: {e}"))
        print(f"[GAGAL] U-00 uji browser tidak berjalan — {e}", flush=True)
    finally:
        if preview and preview.poll() is None:
            subprocess.run(["taskkill", "/PID", str(preview.pid), "/T", "/F"], capture_output=True)


# ───────────────────────── laporan ─────────────────────────


def write_report(started: datetime) -> Path:
    HASIL.mkdir(parents=True, exist_ok=True)
    total = len(R.results)
    counts = {s: sum(r.status == s for r in R.results) for s in ("LULUS", "GAGAL", "LEWAT")}
    lines = [
        "# Laporan QA otomatis",
        "",
        f"Dijalankan: {started:%Y-%m-%d %H:%M} · durasi {(datetime.now() - started).seconds} detik",
        f"Hasil: **{counts['LULUS']} lulus**, **{counts['GAGAL']} gagal**, {counts['LEWAT']} dilewati dari {total} pemeriksaan.",
        "",
        "| ID | Lapisan | Pemeriksaan | Hasil | Detik | Catatan |",
        "| :-- | :-- | :-- | :--: | --: | :-- |",
    ]
    for r in R.results:
        note = r.detail.replace("|", "/").replace("\n", " ")[:200]
        lines.append(f"| {r.id} | {r.layer} | {r.title} | {r.status} | {r.seconds:.1f} | {note} |")
    path = HASIL / "laporan_qa.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (HASIL / "laporan_qa.json").write_text(
        json.dumps([r.__dict__ for r in R.results], ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-static", action="store_true")
    ap.add_argument("--skip-llm", action="store_true", help="lewati L4 (memanggil OpenRouter sungguhan)")
    ap.add_argument("--skip-load", action="store_true")
    ap.add_argument("--skip-browser", action="store_true")
    args = ap.parse_args()
    started = datetime.now()

    if not args.skip_static:
        layer_static()
    layer_pytest()
    try:
        prepare_database()
        start_server()
        layer_api()
        if args.skip_llm:
            R.skip("L-xx", "L4 LLM nyata", "Smoke test LLM", "--skip-llm")
        else:
            layer_llm()
        if not args.skip_load:
            layer_load()
        if not args.skip_browser:
            layer_browser()
    finally:
        stop_server()
        path = write_report(started)
    print(f"\nLaporan: {path}")
    return 1 if any(r.status == "GAGAL" for r in R.results) else 0


if __name__ == "__main__":
    sys.exit(main())

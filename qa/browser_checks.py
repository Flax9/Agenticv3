"""Uji browser (Playwright, Chromium) untuk alur utama UI. Dipanggil oleh run_qa.py, mencetak JSON hasil.

    uv run --with playwright python qa/browser_checks.py http://127.0.0.1:4173 qa_fpp Password-QA-12345

Tidak memanggil LLM: mode bawaan (Tender) dijawab backend dengan pesan tetap.
"""

import json
import sys
import time

from playwright.sync_api import Page, expect, sync_playwright

BASE, USER, PASSWORD = sys.argv[1], sys.argv[2], sys.argv[3]
results = []


def check(id_, title):
    def wrap(fn):
        t0 = time.monotonic()
        try:
            detail = fn() or ""
            status = "LULUS"
        except Exception as e:  # noqa: BLE001
            status, detail = "GAGAL", f"{type(e).__name__}: {str(e)[:1200]}"
            try:
                page.screenshot(path=f"qa/hasil/{id_}.png")
            except Exception:  # noqa: BLE001
                pass
        results.append({"id": id_, "title": title, "status": status, "detail": detail, "seconds": time.monotonic() - t0})
        return fn

    return wrap


def login(page: Page, user: str, password: str) -> None:
    page.goto(BASE)
    page.get_by_label("Username").fill(user)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Masuk").click()


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1366, "height": 800})
    page = ctx.new_page()
    console_errors: list[str] = []
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))

    @check("U-01", "Halaman login tampil dan password salah menampilkan pesan galat tanpa masuk")
    def _():
        page.goto(BASE)
        expect(page.get_by_role("heading", name="Masuk ke akun Anda")).to_be_visible()
        page.get_by_label("Username").fill(USER)
        page.get_by_label("Password").fill("password-salah-123")
        page.get_by_role("button", name="Masuk").click()
        expect(page.get_by_role("alert")).to_be_visible(timeout=15000)
        expect(page.get_by_label("Pesan untuk AI Copilot")).to_have_count(0)
        expect(page.get_by_label("Password")).to_have_value("")  # kolom dikosongkan setelah gagal

    @check("U-02", "Login benar membuka aplikasi dan tanpa galat JavaScript")
    def _():
        console_errors.clear()
        login(page, USER, PASSWORD)
        expect(page.get_by_text("Pilih Jenis Dokumen Pengadaan")).to_be_visible(timeout=20000)
        page.get_by_text("Dokumen Tender Lengkap").click()
        expect(page.get_by_text("Pilih Jenis Dokumen Pengadaan")).to_be_hidden()
        expect(page.get_by_label("Pesan untuk AI Copilot")).to_be_visible(timeout=20000)
        errors = [e for e in console_errors if "401" not in e]
        assert not errors, f"galat konsol: {errors[:3]}"

    @check("U-03", "Sesi login bertahan setelah halaman dimuat ulang (cookie refresh)")
    def _():
        page.reload()
        expect(page.get_by_label("Pesan untuk AI Copilot")).to_be_visible(timeout=20000)
        picker = page.get_by_text("Pilih Jenis Dokumen Pengadaan")
        if picker.is_visible():  # pemilih jenis dokumen tampil lagi setelah muat ulang
            page.get_by_text("Dokumen Tender Lengkap").click()
            expect(picker).to_be_hidden()

    @check("U-04", "Pesan terkirim: gelembung pengguna dan balasan asisten tampil")
    def _():
        box = page.get_by_label("Pesan untuk AI Copilot")
        box.fill("Halo, tolong buatkan dokumen tender")
        page.get_by_role("button", name="Kirim pesan").click()
        expect(page.get_by_text("Halo, tolong buatkan dokumen tender")).to_be_visible(timeout=10000)
        expect(page.get_by_text("belum tersedia", exact=False)).to_be_visible(timeout=30000)

    @check("U-05", "Tampilan ponsel (390 px): tanpa gulir horizontal dan kolom pesan tetap terpakai")
    def _():
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(500)
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert overflow <= 1, f"halaman melebar {overflow}px dari layar"
        expect(page.get_by_label("Pesan untuk AI Copilot")).to_be_visible()
        page.set_viewport_size({"width": 1366, "height": 800})

    @check("U-06", "Keluar: kembali ke halaman login dan tidak bisa masuk lagi tanpa kredensial setelah reload")
    def _():
        page.get_by_label("Buka menu navigasi").click()
        page.get_by_role("menuitem", name="Keluar").click()
        page.get_by_role("alertdialog").get_by_role("button", name="Keluar").click()
        expect(page.get_by_role("heading", name="Masuk ke akun Anda")).to_be_visible(timeout=15000)
        page.reload()
        expect(page.get_by_role("heading", name="Masuk ke akun Anda")).to_be_visible(timeout=15000)

    browser.close()

print(json.dumps(results, ensure_ascii=False))

"""E2E landing + area orang tua di Chromium (Playwright). Dilewati bila Playwright tidak terpasang."""
import os, threading
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
import server as sv

ROOT = Path(__file__).resolve().parent.parent
SHOTS = Path(os.environ.get("SHOT_DIR", "/tmp/shots"))


def _serve(playtest):
    s, _ = sv.build(sv.Config(host="127.0.0.1", port=0, db_path=":memory:", playtest=playtest, public_dir=str(ROOT / "public")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}"


@pytest.fixture(scope="module")
def browser():
    with pw.sync_playwright() as p:
        b = p.chromium.launch(); yield b; b.close()


def _watch(page):
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("console", lambda m: m.type == "error" and "401" not in m.text and "422" not in m.text and errs.append(m.text))
    return errs


def test_landing_renders_and_links_to_register(browser):
    s, base = _serve(True)
    try:
        page = browser.new_page(viewport={"width": 1366, "height": 900}); errs = _watch(page)
        page.goto(base + "/")
        assert "499.000" in page.inner_text("#harga")
        assert page.locator(".weeks li").count() == 13 and page.locator(".weeks li.now").count() <= 1
        page.click("text=Coba diagnostik gratis"); page.wait_for_selector("text=Daftar dan coba diagnostik gratis")
        assert not errs, errs
    finally:
        s.shutdown()


def test_register_shows_code_once_then_login_buy_playtest(browser):
    SHOTS.mkdir(parents=True, exist_ok=True)
    s, base = _serve(True)
    try:
        page = browser.new_page(viewport={"width": 1100, "height": 900}); errs = _watch(page)
        page.goto(base + "/parent/#/daftar")
        page.click("button[type=submit]"); page.wait_for_selector(".err:not([hidden])")
        assert "Centang persetujuan" in page.inner_text(".err") and page.get_attribute("#name", "aria-invalid") == "true"
        page.fill("#name", "Ibu Uji"); page.fill("#whatsapp", "081234567890"); page.fill("#email", "uji@contoh.id"); page.fill("#pin", "246810"); page.check("#consent")
        page.click("button[type=submit]"); page.wait_for_selector(".code")
        code = page.inner_text(".code"); assert len(code) == 9 and code[4] == "-"
        page.screenshot(path=str(SHOTS / "ortu-1-kode.png"))
        page.click("text=Saya sudah mencatat kode"); page.wait_for_selector("h1:has-text('Dashboard')")
        assert code not in page.inner_text("main")                       # kode tidak tampil lagi
        assert "Rp499.000" in page.inner_text("main")
        page.click("#order"); page.wait_for_selector("#pay")
        page.click("#pay"); page.wait_for_selector("text=Paket utama aktif")
        page.screenshot(path=str(SHOTS / "ortu-2-dashboard.png"), full_page=True)

        page.click("#logout"); page.wait_for_selector("h1:has-text('Masuk')")
        page.fill("#email", "uji@contoh.id"); page.fill("#pin", "000000"); page.click("button[type=submit]")
        page.wait_for_selector(".err:not([hidden])"); assert "tidak cocok" in page.inner_text(".err")
        page.fill("#pin", "246810"); page.click("button[type=submit]"); page.wait_for_selector("text=Paket utama aktif")
        assert not errs, errs
    finally:
        s.shutdown()


def test_production_mode_has_no_fake_pay_button(browser):
    s, base = _serve(False)
    try:
        page = browser.new_page(); errs = _watch(page)
        page.goto(base + "/parent/#/daftar")
        page.fill("#name", "Ibu"); page.fill("#whatsapp", "081234567890"); page.fill("#email", "p@contoh.id"); page.fill("#pin", "135791"); page.check("#consent")
        page.click("button[type=submit]"); page.click("text=Saya sudah mencatat kode")
        page.wait_for_selector("text=Pembayaran online segera dibuka")
        assert page.locator("#order, #pay").count() == 0
        assert not errs, errs
    finally:
        s.shutdown()

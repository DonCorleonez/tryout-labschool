"""E2E landing + area orang tua di Chromium (Playwright). Dilewati bila Playwright tidak terpasang."""
import os, threading
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
import server as sv

ROOT = Path(__file__).resolve().parent.parent
SHOTS = Path(os.environ.get("SHOT_DIR", "/tmp/shots"))
QA_SHOTS = ROOT / "docs" / "qa-screenshots"


def _serve(playtest, bank_dir=""):
    s, _ = sv.build(sv.Config(host="127.0.0.1", port=0, db_path=":memory:", playtest=playtest, public_dir=str(ROOT / "public"), bank_dir=bank_dir))
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
    QA_SHOTS.mkdir(parents=True, exist_ok=True)
    s, base = _serve(True)
    page = browser.new_page(viewport={"width": 1366, "height": 900}); errs = _watch(page)
    try:
        page.goto(base + "/")
        harga_txt = page.inner_text("#harga")
        assert "TBD" in harga_txt and "9 Des 2026" in harga_txt and "jendela tersisa" in harga_txt
        assert "keluarga" not in page.inner_text("body").lower()
        assert page.locator(".weeks li").count() == 13 and page.locator(".weeks li.now").count() <= 1
        page.screenshot(path=str(QA_SHOTS / "landing-desktop.png"), full_page=True)
        # Cek demo interaktif 1 soal (salah -> AWAS JEBAKAN + CARA CEPAT; benar -> kartu hijau)
        page.click(".demo-opt[data-choice='A']")
        page.wait_for_selector("#demo-trap:not([hidden])")
        assert "AWAS JEBAKAN" in page.inner_text("#demo-trap")
        page.click("#demo-retry"); page.click(".demo-opt[data-choice='B']")
        assert "benar" in page.inner_text("#demo-fb-title").lower()
        # Cek modal paywall terpadu (konsisten jendela tersisa & waktu pemesanan, tanpa klaim mutlak seluruh 14 tryout)
        page.click("#open-paywall"); page.wait_for_selector("#paywall-modal:not([hidden])")
        modal_txt = page.inner_text("#paywall-modal")
        assert "Hingga 14 Tryout" in modal_txt and "Buka seluruh 14 Tryout" not in modal_txt
        assert "jendela yang sudah lewat tidak digulung ulang" in modal_txt
        assert "pemesanan s.d. 8 Des 2026" in modal_txt and "pemesanan mulai 9 Des 2026" in modal_txt
        page.click("#close-paywall")
        page.click("text=Cek kesiapan anak, gratis"); page.wait_for_selector("text=Daftar dan coba diagnostik gratis")
        assert not errs, errs
    finally:
        page.close()
        s.shutdown(); s.server_close()


def test_register_shows_code_once_then_login_buy_playtest(browser):
    SHOTS.mkdir(parents=True, exist_ok=True)
    s, base = _serve(True)
    page = browser.new_page(viewport={"width": 1100, "height": 900}); errs = _watch(page)
    try:
        page.goto(base + "/parent/#/daftar")
        page.click("button[type=submit]"); page.wait_for_selector(".err:not([hidden])")
        assert "Centang persetujuan" in page.inner_text(".err") and page.get_attribute("#name", "aria-invalid") == "true"
        page.fill("#name", "Ibu Uji"); page.fill("#whatsapp", "081234567890"); page.fill("#email", "uji@contoh.id"); page.fill("#pin", "246810"); page.check("#consent")
        page.click("button[type=submit]"); page.wait_for_selector(".code")
        code = page.inner_text(".code"); assert len(code) == 9 and code[4] == "-"
        dev_id = page.evaluate("localStorage.getItem('tryout_device_id')")
        assert dev_id and dev_id.startswith("dev_")
        page.screenshot(path=str(SHOTS / "ortu-1-kode.png"))
        page.click("text=Saya sudah mencatat kode"); page.wait_for_selector("h1:has-text('Dashboard')")
        assert code not in page.inner_text("main")                       # kode tidak tampil lagi
        assert "Rp99.000" in page.inner_text("main")
        page.click("#order"); page.wait_for_selector("#pay")
        page.click("#pay"); page.wait_for_selector("text=Paket utama aktif")
        page.screenshot(path=str(SHOTS / "ortu-2-dashboard.png"), full_page=True)

        page.click("#logout"); page.wait_for_selector("h1:has-text('Masuk')")
        page.fill("#email", "uji@contoh.id"); page.fill("#pin", "000000"); page.click("button[type=submit]")
        page.wait_for_selector(".err:not([hidden])"); assert "tidak cocok" in page.inner_text(".err")
        page.fill("#pin", "246810"); page.click("button[type=submit]"); page.wait_for_selector("text=Paket utama aktif")
        assert not errs, errs
    finally:
        page.close()
        s.shutdown(); s.server_close()


def test_production_mode_has_no_fake_pay_button(browser):
    s, base = _serve(False)
    page = browser.new_page(); errs = _watch(page)
    try:
        page.goto(base + "/parent/#/daftar")
        page.fill("#name", "Ibu"); page.fill("#whatsapp", "081234567890"); page.fill("#email", "p@contoh.id"); page.fill("#pin", "135791"); page.check("#consent")
        page.click("button[type=submit]"); page.click("text=Saya sudah mencatat kode")
        page.wait_for_selector("text=Pembayaran online segera dibuka")
        assert page.locator("#order, #pay").count() == 0
        assert not errs, errs
    finally:
        page.close()
        s.shutdown(); s.server_close()


def test_full_end_to_end_daftar_tryout_report_drill_buku_salah_and_mobile(browser):
    """Acceptance 4: alur daftar -> tryout -> report -> drill -> Buku Salah end-to-end + cek HP 375px."""
    import json, urllib.request
    SHOTS.mkdir(parents=True, exist_ok=True)
    QA_SHOTS.mkdir(parents=True, exist_ok=True)
    s, base = _serve(True)
    page = browser.new_page(viewport={"width": 1280, "height": 900}); errs = _watch(page)
    cpage = None; mpage = None
    try:
        # 1. Daftar orang tua & ambil kode akses + pastikan header X-Device-Id dikirim
        seen_dev_hdrs = []
        page.on("request", lambda req: "/api/" in req.url and req.headers.get("x-device-id") and seen_dev_hdrs.append(req.headers["x-device-id"]))
        page.goto(base + "/parent/?sim=2026-11-04T10:00#/daftar")
        page.fill("#name", "Ibu E2E"); page.fill("#whatsapp", "081299990001")
        page.fill("#email", "full@contoh.id"); page.fill("#pin", "246810")
        page.select_option("#campus", "Cibubur"); page.select_option("#track", "Jalur Tes"); page.select_option("#grade", "6")
        page.check("#consent"); page.click("button[type=submit]")
        page.wait_for_selector(".code")
        assert seen_dev_hdrs and seen_dev_hdrs[0].startswith("dev_")
        code = page.inner_text(".code")
        assert "LAB-" + code in page.inner_text("main")
        page.click("text=Saya sudah mencatat kode"); page.wait_for_selector("h1:has-text('Dashboard')")
        page.click("#order"); page.wait_for_selector("#pay"); page.click("#pay")
        page.wait_for_selector("text=Paket utama aktif")

        # 2. Anak login pakai LAB-XXXX-XXXX di jendela tryout -> beranda -> kerjakan DIAG -> hasil (bintang + XP + level)
        cpage = browser.new_page(viewport={"width": 1280, "height": 860}); cerrs = _watch(cpage)
        cpage.goto(base + "/child/?sim=2026-11-06T18:00")
        cpage.fill("#code", "LAB-" + code); cpage.click("button[type=submit]")
        cpage.wait_for_selector("text=Diagnostik")
        cpage.screenshot(path=str(QA_SHOTS / "child-beranda.png"), full_page=True)
        cpage.click("[data-start=DIAG]"); cpage.wait_for_selector(".opts")
        cpage.click(".opt[data-i='0']"); cpage.click("#grid"); cpage.wait_for_selector("#g-check")
        cpage.click("#g-check"); cpage.wait_for_selector("#send"); cpage.click("#send")
        cpage.wait_for_selector("text=Tryout terkumpul")
        cpage.screenshot(path=str(SHOTS / "e2e-child-hasil.png"), full_page=True)
        cpage.screenshot(path=str(QA_SHOTS / "child-hasil.png"), full_page=True)
        assert "XP" in cpage.inner_text("main") and "Level" in cpage.inner_text("header")

        # 3. Proses stand-in analisis admin (Minggu 22.00)
        req = urllib.request.Request(base + "/api/admin/analysis/standin", data=b"{}",
                                     headers={"Content-Type": "application/json", "X-Admin-Token": "dev-admin", "X-Sim-Time": "2026-11-08T22:00"}, method="POST")
        assert json.loads(urllib.request.urlopen(req).read())["diproses"] == 1

        # 4. Senin: Anak kerjakan drill & buka Buku Salah
        cpage.goto(base + "/child/?sim=2026-11-09T10:00#/drill")
        cpage.wait_for_selector("button:has-text('Mulai Drill')")
        cpage.click("button:has-text('Mulai Drill')"); cpage.wait_for_selector(".opts")
        for _ in range(5):
            cpage.click(".opt[data-i='0']")
            if cpage.locator("#d-next").count():
                cpage.click("#d-next")
            else:
                cpage.click("#d-finish"); break
        cpage.wait_for_selector("text=Drill Selesai!")
        cpage.goto(base + "/child/?sim=2026-11-09T10:05#/buku-salah")
        cpage.wait_for_selector("text=Buku Salah")
        cpage.screenshot(path=str(QA_SHOTS / "child-buku-salah.png"), full_page=True)
        assert "Cara cepat" in cpage.inner_text("main") or "CARA CEPAT" in cpage.inner_text("main")

        # 5. Senin 07.05: Orang tua buka Laporan 60-Detik, Buku Salah Cetak, & Jalur Prestasi
        page.goto(base + "/parent/?sim=2026-11-09T07:05#/beranda")
        page.wait_for_selector("text=Laporan Kesiapan Siswa")
        rep_text = page.inner_text("main")
        assert "tryout dikerjakan" in rep_text.lower() and "konsistensi drill" in rep_text.lower()
        assert "bintang" not in rep_text.lower() and "xp" not in rep_text.lower() and "dijamin lolos" not in rep_text.lower()
        page.screenshot(path=str(SHOTS / "e2e-parent-report.png"), full_page=True)
        page.screenshot(path=str(QA_SHOTS / "parent-report.png"), full_page=True)
        page.click("#tab-buku-salah"); page.wait_for_selector("text=Buku Salah Cetak")
        page.click("#tab-prestasi"); page.wait_for_selector("text=Jalur Prestasi")
        page.fill("#proof-ref", "CERT-2026-E2E"); page.click("button[type=submit]")
        page.wait_for_selector("#prestasi-code")
        assert "TBD" in page.inner_text("main")

        # 6. Cek tampilan HP 375px (landing + parent report) tidak meluber horizontal
        mpage = browser.new_page(viewport={"width": 375, "height": 812}); merrs = _watch(mpage)
        mpage.goto(base + "/")
        overflow_land = mpage.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert overflow_land <= 2, f"Landing mobile overflow: {overflow_land}"
        mpage.screenshot(path=str(SHOTS / "e2e-mobile-landing.png"), full_page=True)
        mpage.screenshot(path=str(QA_SHOTS / "landing-mobile-375.png"), full_page=True)
        assert not errs and not cerrs and not merrs, (errs, cerrs, merrs)
    finally:
        for p in (mpage, cpage, page):
            if p: p.close()
        s.shutdown(); s.server_close()


def test_canonical_bank_subjects_and_mobile_portals_in_browser(tmp_path, browser):
    """Verifikasi bank kanonik (5 mapel resmi batch_01.json) + interaksi mobile 375px portal anak & orang tua."""
    import json, re, shutil, urllib.request
    import bank
    bdir = tmp_path / "canonical_bank"; bdir.mkdir()
    shutil.copy2(ROOT / "reference" / "testdata" / "batch_01.json", bdir / "batch_01.json")
    QA_SHOTS.mkdir(parents=True, exist_ok=True)
    s, base = _serve(True, bank_dir=str(bdir))
    page = browser.new_page(viewport={"width": 1280, "height": 900}); errs = _watch(page)
    cpage = browser.new_page(viewport={"width": 375, "height": 812}); cerrs = _watch(cpage)
    pmpage = browser.new_page(viewport={"width": 375, "height": 812}); perrs = _watch(pmpage)
    try:
        # 1. Daftar & bayar Paket Utama
        page.goto(base + "/parent/?sim=2026-11-04T10:00#/daftar")
        page.fill("#name", "Ibu Kanonik"); page.fill("#whatsapp", "081288880001")
        page.fill("#email", "kanonik@contoh.id"); page.fill("#pin", "246810")
        page.check("#consent"); page.click("button[type=submit]")
        page.wait_for_selector(".code"); code = page.inner_text(".code")
        page.click("text=Saya sudah mencatat kode"); page.wait_for_selector("h1:has-text('Dashboard')")
        page.click("#order"); page.wait_for_selector("#pay"); page.click("#pay")
        page.wait_for_selector("text=Paket utama aktif")

        # 2. Anak login & kerjakan DIAG 40 soal bank kanonik di HP 375px -> cek 0 overflow & 5 mapel resmi
        cpage.goto(base + "/child/?sim=2026-11-06T18:00")
        cpage.fill("#code", "LAB-" + code); cpage.click("button[type=submit]")
        cpage.wait_for_selector("text=Diagnostik")
        overflow_child_home = cpage.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert overflow_child_home <= 2, f"Child mobile home overflow: {overflow_child_home}"
        cpage.screenshot(path=str(QA_SHOTS / "child-mobile-375.png"))
        cpage.click("[data-start=DIAG]"); cpage.wait_for_selector(".opts")
        assert "dari 40" in cpage.inner_text(".qhead")
        cpage.click(".opt[data-i='0']"); cpage.click("#grid"); cpage.wait_for_selector("#g-check")
        cpage.click("#g-check"); cpage.wait_for_selector("#send"); cpage.click("#send")
        cpage.wait_for_selector("text=Tryout terkumpul")
        res_txt = cpage.inner_text("main")
        for subj in ("Kuantitatif", "Pemahaman Bacaan", "Verbal", "IPA", "IPS"):
            assert subj in res_txt
        assert not re.search(r"(?m)^(?:Bahasa Indonesia|Matematika)\b", res_txt)
        cpage.screenshot(path=str(QA_SHOTS / "child-hasil.png"), full_page=True)

        # 3. Stand-in analisis Minggu 22.00 -> Senin anak buka Buku Salah -> Orang tua buka Report Desktop & Mobile 375px
        req = urllib.request.Request(base + "/api/admin/analysis/standin", data=b"{}",
                                     headers={"Content-Type": "application/json", "X-Admin-Token": "dev-admin", "X-Sim-Time": "2026-11-08T22:00"}, method="POST")
        assert json.loads(urllib.request.urlopen(req).read())["diproses"] == 1

        cpage.goto(base + "/child/?sim=2026-11-09T10:05#/buku-salah")
        cpage.wait_for_selector("text=Buku Salah")
        cpage.screenshot(path=str(QA_SHOTS / "child-buku-salah.png"), full_page=True)

        page.goto(base + "/parent/?sim=2026-11-09T07:05#/beranda")
        page.wait_for_selector("text=Laporan Kesiapan Siswa")
        rep_txt = page.inner_text("main")
        for subj in ("Kuantitatif", "Pemahaman Bacaan", "Verbal", "IPA", "IPS"):
            assert subj in rep_txt
        assert not re.search(r"(?m)^(?:Bahasa Indonesia|Matematika)\b", rep_txt)
        page.screenshot(path=str(QA_SHOTS / "parent-report.png"), full_page=True)

        pmpage.goto(base + "/parent/?sim=2026-11-09T07:05#/masuk")
        pmpage.fill("#email", "kanonik@contoh.id"); pmpage.fill("#pin", "246810"); pmpage.click("button[type=submit]")
        pmpage.wait_for_selector("text=Laporan Kesiapan Siswa")
        overflow_parent = pmpage.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert overflow_parent <= 2, f"Parent mobile report overflow: {overflow_parent}"
        pmpage.screenshot(path=str(QA_SHOTS / "parent-mobile-375.png"))
        pmpage.click("#tab-buku-salah"); pmpage.wait_for_selector("text=Buku Salah Cetak")
        pmpage.click("#tab-prestasi"); pmpage.wait_for_selector("text=Jalur Prestasi")
        assert not errs and not cerrs and not perrs, (errs, cerrs, perrs)
    finally:
        for p in (pmpage, cpage, page):
            if p: p.close()
        s.shutdown(); s.server_close()
        bank.configure(None)


def test_late_joiner_and_cross_cutoff_order_in_browser(browser):
    """Regresi E2E: daftar 8 Des lalu order mulai 9 Des (Kejar Rp129.000) & akses jendela tersisa (9 tryout)."""
    s, base = _serve(True)
    page = browser.new_page(viewport={"width": 1200, "height": 900}); errs = _watch(page)
    try:
        # 1. Daftar 8 Des 20.00 WIB -> penawaran dashboard sebelum order masih Paket Utama + tanggal pemesanan eksplisit
        page.goto(base + "/parent/?sim=2026-12-08T20:00#/daftar")
        page.fill("#name", "Ibu Lintas"); page.fill("#whatsapp", "081277770001")
        page.fill("#email", "lintas@contoh.id"); page.fill("#pin", "246810")
        page.check("#consent"); page.click("button[type=submit]")
        page.wait_for_selector(".code")
        page.click("text=Saya sudah mencatat kode"); page.wait_for_selector("h1:has-text('Dashboard')")
        pre_txt = page.inner_text("main")
        assert "Paket utama" in pre_txt and "Rp99.000" in pre_txt and "pemesanan s.d. 8 Des 2026" in pre_txt

        # 2. Melewati 9 Des 00.00 WIB sebelum order -> tawaran beralih ke Paket Kejar Rp129.000 (9 tryout tersisa)
        page.goto(base + "/parent/?sim=2026-12-10T10:00#/beranda")
        page.wait_for_selector("text=Paket kejar")
        post_txt = page.inner_text("main")
        assert "Paket kejar" in post_txt and "Rp129.000" in post_txt and "9 tryout pada jendela tersisa" in post_txt
        assert "Pemesanan mulai 9 Des 2026" in post_txt
        page.click("#order"); page.wait_for_selector("#pay")
        page.click("#pay"); page.wait_for_selector("text=Paket kejar aktif.")
        assert not errs, errs
    finally:
        page.close()
        s.shutdown(); s.server_close()

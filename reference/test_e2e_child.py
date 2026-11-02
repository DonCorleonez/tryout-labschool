"""E2E layar anak di Chromium nyata (Playwright). Dilewati bila Playwright tidak terpasang.
Skenario: masuk → beranda → tryout (keyboard, ragu, grid) → refresh di tengah (lanjut) → periksa → kumpulkan → hasil."""
import json, os, threading, urllib.request
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
import server as sv

ROOT = Path(__file__).resolve().parent.parent
SHOTS = Path(os.environ.get("SHOT_DIR", "/tmp/shots"))
SIM = "2026-11-06T18:00"


@pytest.fixture(scope="module")
def base():
    cfg = sv.Config(host="127.0.0.1", port=0, db_path=":memory:", playtest=True, public_dir=str(ROOT / "public"))
    s, _ = sv.build(cfg)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_address[1]}"
    s.shutdown()


def _post(base, path, body, hdr=None):
    r = urllib.request.Request(base + path, json.dumps(body).encode(), {"Content-Type": "application/json", "X-Sim-Time": SIM, **(hdr or {})}, method="POST")
    return json.loads(urllib.request.urlopen(r).read())


@pytest.fixture(scope="module")
def browser():
    with pw.sync_playwright() as p:
        b = p.chromium.launch(); yield b; b.close()


def test_child_full_flow_with_refresh_resume(base, browser):
    code = _post(base, "/api/parent/register", {"name": "Ibu", "whatsapp": "081234567890", "email": "e2e@x.co", "consent": True, "pin": "123456"})["child_code"]
    SHOTS.mkdir(parents=True, exist_ok=True)
    page = browser.new_page(viewport={"width": 1280, "height": 860}); errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.goto(f"{base}/child/?sim={SIM}")

    page.fill("#code", "zzzz-9999"); page.click("button[type=submit]")
    page.wait_for_selector(".err:not([hidden])"); assert "belum dikenali" in page.inner_text(".err")
    errors.clear()                                                   # 401 dari kode salah memang diharapkan
    page.fill("#code", code.replace("-", "").lower())            # format otomatis ke ABCD-1234
    assert page.input_value("#code") == code
    page.click("button[type=submit]")
    page.wait_for_selector("text=Diagnostik"); page.screenshot(path=str(SHOTS / "anak-1-beranda.png"))
    assert "Jendela tryout sedang dibuka" in page.inner_text("main")

    page.click("[data-start=DIAG]"); page.wait_for_selector(".opts")
    assert "dari 12" in page.inner_text(".qhead")
    page.keyboard.press("b"); assert page.get_attribute(".opt[data-i='1']", "aria-checked") == "true"
    page.click("#flag"); assert page.get_attribute("#flag", "aria-pressed") == "true"
    page.keyboard.press("n"); page.keyboard.press("3"); page.keyboard.press("n"); page.click(".opt[data-i='0']")
    page.screenshot(path=str(SHOTS / "anak-2-soal.png"))
    page.wait_for_timeout(300)

    page.reload(); page.wait_for_selector(".opts")                          # refresh: lanjut, jawaban tetap
    assert "Melanjutkan" in page.inner_text("#toast")
    page.click("#grid"); page.wait_for_selector(".sheet")
    assert page.locator(".sheet .cell.ans").count() == 3 and page.locator(".sheet .cell .fm").count() == 1
    page.screenshot(path=str(SHOTS / "anak-3-grid.png"))
    page.click("#g-check"); page.wait_for_selector("text=Periksa sebelum mengumpulkan")
    assert "3</strong> dari 12" in page.inner_html("main")
    page.screenshot(path=str(SHOTS / "anak-4-periksa.png"))
    page.click("#send"); page.wait_for_selector("text=Tryout terkumpul")
    assert page.locator(".score").inner_text().endswith("/12")
    page.screenshot(path=str(SHOTS / "anak-5-hasil.png"), full_page=True)
    assert "Jawaban benar" in page.inner_text("main") and "Yang perlu dilatih lagi" in page.inner_text("main") and "salah " in page.inner_text(".topics")

    page.goto(f"{base}/child/#/beranda"); page.wait_for_selector("text=Sudah dikumpulkan")
    assert not errors, errors


def test_mobile_layout_has_warning_and_no_errors(base, browser):
    code = _post(base, "/api/parent/register", {"name": "Ibu", "whatsapp": "081234567891", "email": "m@x.co", "consent": True, "pin": "123456"})["child_code"]
    page = browser.new_page(viewport={"width": 375, "height": 740}); errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{base}/child/?sim={SIM}"); page.fill("#code", code); page.click("button[type=submit]")
    page.click("[data-start=DIAG]"); page.wait_for_selector(".opts")
    assert page.is_visible(".small-warn")
    box = page.locator(".opt").first.bounding_box(); assert box["height"] >= 44
    page.screenshot(path=str(SHOTS / "anak-6-ponsel.png"))
    assert not errors, errors


def test_outside_window_shows_closed_message(base, browser):
    code = _post(base, "/api/parent/register", {"name": "Ibu", "whatsapp": "081234567892", "email": "w@x.co", "consent": True, "pin": "123456"})["child_code"]
    page = browser.new_page()
    page.goto(f"{base}/child/?sim=2026-11-10T10:00"); page.fill("#code", code); page.click("button[type=submit]")
    page.wait_for_selector(".note")
    assert "drill" in page.inner_text(".note").lower()

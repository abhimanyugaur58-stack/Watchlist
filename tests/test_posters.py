"""Posters from (fake) TVmaze, the poster picker, offline posters, and the brass seal."""
import base64
import json
import sys
import time

from playwright.sync_api import sync_playwright
from common import APP_URL as URL, OUT, KEY, FIXTURE, Checker, FakeTVmaze

check = Checker()


def wait_for(pg, js, timeout=15000):
    t0 = time.time()
    while time.time() - t0 < timeout / 1000:
        if pg.evaluate(js):
            return True
        pg.wait_for_timeout(150)
    return False


with sync_playwright() as p:
    b = p.chromium.launch()
    fake = FakeTVmaze()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    fake.attach(ctx)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    st = lambda: pg.evaluate("k => JSON.parse(localStorage.getItem(k))", KEY)
    ls = lambda k: pg.evaluate("k => localStorage.getItem(k)", k)

    # Fresh device with the saved list: posters arrive by themselves.
    pg.goto(URL)
    pg.evaluate("([k, s]) => { localStorage.clear(); localStorage.setItem(k, JSON.stringify(s)); }", [KEY, FIXTURE])
    pg.goto(URL)
    # Typing while posters arrive must not lose the text.
    pg.click("#tabs .fab")
    pg.fill("#add-name", "आधा लिखा नाम")
    got_suits = wait_for(pg, "localStorage.getItem('wl-poster:172') !== null")
    check(got_suits, "Suits poster fetched and kept")
    pg.wait_for_timeout(1500)
    check(pg.input_value("#add-name") == "आधा लिखा नाम", "text being typed survives posters arriving")
    pg.go_back()
    wait_for(pg, "localStorage.getItem('wl-poster:82') !== null", 30000)
    check(ls("wl-poster:269") is not None and ls("wl-poster:82") is not None, "own series Peaky Blinders and GoT got posters by name")
    check(pg.locator("#scr-now .card[aria-label='अभी देख रहे हैं'] img.tile.poster").count() == 1, "Now card shows the poster")
    check(pg.locator("#scr-now .upnext img.tile.sm").count() == 2, "up-next rows show small posters")
    size = len(ls("wl-poster:172"))
    check(1000 < size < 80000, f"poster stored at a small size ({size} chars)")
    check(all(c.startswith("/shows/") or c.startswith("/search/") for c in fake.api_calls), "only show and search calls")
    check(not any(c.startswith("/search/") for c in fake.api_calls), "no searching needed for known series")
    pg.screenshot(path=str(OUT / "p01-now.png"))

    # Restart offline: posters still there, no network needed.
    n_img = len(fake.img_calls)
    fake.offline = True
    pg.goto(URL)
    pg.wait_for_timeout(1500)
    check(pg.locator("#scr-now .card[aria-label='अभी देख रहे हैं'] img.tile.poster").count() == 1, "offline: poster still shows")
    fake.offline = False
    pg.goto(URL)
    pg.wait_for_timeout(2500)
    check(len(fake.img_calls) == n_img, "posters are not downloaded again")

    # Detail: big poster over a blurred backdrop.
    pg.click("#scr-now .name-lg")
    hero_bg = pg.evaluate("getComputedStyle(document.querySelector('#scr-detail .hero-bg'), '::before').backgroundImage")
    check(hero_bg.startswith('url("data:image'), "detail backdrop uses the poster")
    check(pg.locator("#scr-detail .poster-btn img.tile.big").count() == 1, "detail shows the big poster")
    pg.screenshot(path=str(OUT / "p02-detail.png"))

    # Picker: choose another show, then go back to the app's own choice.
    pg.click("#scr-detail .poster-btn")
    pg.wait_for_selector("#scr-detail .pick")
    check(pg.locator("#scr-detail .pick").count() == 2 and "Suits LA" in pg.inner_text("#scr-detail .picks"), "picker lists search results")
    pg.screenshot(path=str(OUT / "p03-picker.png"), full_page=True)
    pg.click("#scr-detail .pick >> text=Suits LA")
    wait_for(pg, "document.querySelector('#scr-detail .poster-btn img') !== null")
    s = st()
    check(s["tv"].get("suits") == 500172, "picked show saved for this series")
    check(wait_for(pg, "localStorage.getItem('wl-poster:500172') !== null"), "picked poster stored")
    pg.click("#snack-undo")
    check("suits" not in st().get("tv", {}), "undo puts the old poster back")
    pg.click("#scr-detail .poster-btn")
    pg.wait_for_selector("#scr-detail .pick")
    pg.click("#scr-detail >> text=पोस्टर नहीं चाहिए")
    check(st()["tv"].get("suits") == 0 and pg.locator("#scr-detail .poster-btn div.tile.big").count() == 1, "no poster: letter tile")
    pg.click("#scr-detail .poster-btn")
    pg.wait_for_selector("#scr-detail .pick")
    pg.click("#scr-detail >> text=ऐप वाला पोस्टर")
    wait_for(pg, "document.querySelector('#scr-detail .poster-btn img') !== null")
    check("suits" not in st()["tv"] and pg.locator("#scr-detail .poster-btn img.tile.big").count() == 1, "back to the app's poster")

    # A series added by hand finds its poster when the name matches exactly.
    pg.go_back()
    pg.click("#tabs .fab")
    pg.fill("#add-name", "Yellowstone")
    pg.fill("#add-seasons", "5"); pg.fill("#add-eps", "10")
    pg.click("#scr-add button[type=submit]")
    cid = [k for k, v in st()["custom"].items() if v["name"] == "Yellowstone"][0]
    check(wait_for(pg, f"(JSON.parse(localStorage.getItem('{KEY}')).tv || {{}})['{cid}'] > 0"), "own series matched by exact name")
    tv = st()["tv"][cid]
    check(wait_for(pg, f"localStorage.getItem('wl-poster:{tv}') !== null"), "own series poster stored")
    pg.wait_for_timeout(300)
    check(pg.locator(f"#scr-queue img.tile.sm[data-series='{cid}']").count() == 1, "queue row shows the new poster")
    pg.screenshot(path=str(OUT / "p04-queue.png"))

    # Backup carries the poster choices, not the pictures.
    pg.click("#tabs .tab >> text=अभी")
    pg.click("#scr-now [aria-label^='सेटिंग और बैकअप']")
    pg.click("#scr-settings >> text=बैकअप कोड कॉपी करें")
    pg.wait_for_timeout(200)
    code = pg.input_value("#backup-out")
    data = json.loads(base64.b64decode(code[4:]).decode("utf-8"))
    check(data.get("tv", {}).get(cid) == tv and "wl-poster" not in code, "backup holds poster choices only")
    credit = pg.get_attribute("#scr-settings a >> text=TVmaze", "href")
    check(credit == "https://www.tvmaze.com", "TVmaze credited with a link")

    # Finishing a series: the brass seal.
    pg.evaluate("k => { const s = JSON.parse(localStorage.getItem(k)); s.progress.suits = { s: 9, e: 10 }; localStorage.setItem(k, JSON.stringify(s)); }", KEY)
    pg.goto(URL)
    pg.click("#scr-now >> text=पूरी सीरीज़ देख ली ✓")
    check(pg.is_visible(".seal-overlay") and "पूरी हुई" in pg.inner_text(".seal-overlay") and "Suits" in pg.inner_text(".seal-overlay"), "seal shows on finishing")
    pg.wait_for_timeout(250)
    pg.screenshot(path=str(OUT / "p05-seal.png"))
    pg.wait_for_timeout(2800)
    check(pg.locator(".seal-overlay").count() == 0, "seal goes away by itself")
    pg.click("#tabs .tab >> text=सूची")
    check(pg.locator("#scr-queue .qrow.done svg.seal").count() == 1, "finished row in the list carries a small seal")
    pg.click("#tabs .tab >> text=देख लीं")
    pg.screenshot(path=str(OUT / "p06-finished.png"))

    # Empty diary art.
    pg.evaluate("k => { const s = JSON.parse(localStorage.getItem(k)); s.done = []; s.finishedOrder = []; localStorage.setItem(k, JSON.stringify(s)); }", KEY)
    pg.goto(URL)
    pg.click("#tabs .tab >> text=देख लीं")
    check(pg.locator("#scr-finished .empty-art svg.seal.outline").count() == 1, "empty diary shows the outline seal")
    check(not errors, "no JS errors: " + "; ".join(errors))
    ctx.close()

    # Tablet sideways for a look.
    ctx = b.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=1.5, is_mobile=True, has_touch=True)
    FakeTVmaze().attach(ctx)
    pg = ctx.new_page()
    pg.goto(URL)
    pg.evaluate("([k, s]) => { localStorage.clear(); localStorage.setItem(k, JSON.stringify(s)); localStorage.setItem('wl-seen-build', '99'); }", [KEY, FIXTURE])
    pg.goto(URL)
    wait_for(pg, "localStorage.getItem('wl-poster:13417') !== null", 30000)
    pg.click("#tabs .tab >> text=सूची")
    pg.wait_for_timeout(400)
    pg.screenshot(path=str(OUT / "p07-tablet-queue.png"))
    pg.click("#tabs .tab >> text=अभी")
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT / "p08-tablet-now.png"))
    b.close()
sys.exit(check.done())

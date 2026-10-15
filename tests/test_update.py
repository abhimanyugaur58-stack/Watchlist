"""Live update: starter page + bundled page + downloads from GitHub Pages (network faked with page.route)."""
import json
import re
import shutil
import sys

from playwright.sync_api import sync_playwright
from common import REPO, APP, OUT, KEY, FIXTURE, Checker, NO_INTRO

check = Checker()
LIVE = "https://abhimanyugaur58-stack.github.io/Watchlist/"

# Fake APK assets folder: the starter page plus the bundled app page.
assets = OUT / "assets"
shutil.rmtree(assets, ignore_errors=True)
assets.mkdir(parents=True)
shutil.copy(REPO / "android" / "assets" / "index.html", assets / "index.html")
LOADER = (assets / "index.html").as_uri()
docs_src = APP.read_text(encoding="utf-8")
docs_build = int(re.search(r"const BUILD = (\d+);", docs_src).group(1))
base_build = int(re.search(r"var BUNDLED = (\d+);", (assets / "index.html").read_text(encoding="utf-8")).group(1))
assert docs_build >= base_build, "docs/app.html must never be older than the page bundled in the APK"
# The bundled copy as the APK has it: today's page, numbered like the APK's own copy.
page_src = docs_src.replace(f"const BUILD = {docs_build};", f"const BUILD = {base_build};")
(assets / "app.html").write_text(page_src, encoding="utf-8")
FAR = 100  # fake online builds sit far above every real one


def variant(build, version, extra=""):
    s = page_src.replace(f"const BUILD = {base_build};", f"const BUILD = {build};")
    s = re.sub(r'const VERSION = "[^"]+";', f'const VERSION = "{version}";', s)
    s = s.replace("const CHANGES = {", "const CHANGES = {\n  " + str(build) + ': ["परीक्षण वाला नया बदलाव ' + version + '"],', 1)
    assert str(build) + ": [" not in page_src
    return s.replace("'use strict';", "'use strict';" + extra, 1)


remote = {}


def serve(route):
    name = route.request.url[len(LIVE):].split("?")[0]
    if remote.get("offline"):
        return route.abort()
    body = remote.get(name)
    if body is None:
        return route.fulfill(status=404, body="not found", headers={"Access-Control-Allow-Origin": "*"})
    ctype = "application/json" if name.endswith(".json") else "text/html; charset=utf-8"
    route.fulfill(status=200, body=body, headers={"Content-Type": ctype, "Access-Control-Allow-Origin": "*"})


def publish(build, version, page=None, min_shell=3):
    remote["version.json"] = json.dumps({"build": build, "version": version, "minShell": min_shell})
    if page is not None:
        remote["app.html"] = page


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    ctx.add_init_script(NO_INTRO)
    ctx.route(LIVE + "**", serve)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    ls = lambda k: pg.evaluate("k => localStorage.getItem(k)", k)
    st = lambda: pg.evaluate("k => JSON.parse(localStorage.getItem(k))", KEY)
    txt = lambda sel: pg.inner_text(sel)

    def start():
        pg.goto(LOADER)
        pg.wait_for_selector("#scr-now .card", timeout=8000)

    def open_settings():
        if pg.is_visible("#tabs .tab.settings"):
            pg.click("#tabs .tab.settings")
        else:
            pg.click("#scr-now [aria-label^='सेटिंग और बैकअप']")

    # Same version online as in the APK.
    publish(base_build, "3.0", page_src)
    pg.goto(LOADER)
    pg.evaluate("([k, s]) => { localStorage.clear(); localStorage.setItem(k, JSON.stringify(s)); }", [KEY, FIXTURE])
    start()
    check(pg.url.endswith("/app.html?shell=3"), "no download yet: starter page opens the bundled page " + pg.url)
    check("110 / 134" in txt("#scr-now"), "saved list shows (Suits 110/134)")
    pg.wait_for_timeout(1800)
    check(ls("wl-last-check") is not None and ls("wl-code") is None, "auto check ran, nothing downloaded when up to date")
    open_settings()
    s_txt = txt("#scr-settings")
    check("सबसे नया संस्करण" in s_txt and "ढाँचा 3" in s_txt, "settings: up to date, shell 3")
    pg.screenshot(path=str(OUT / "u01-latest.png"), full_page=True)

    # A new version goes online.
    publish(base_build + FAR + 1, "3.1", variant(base_build + FAR + 1, "3.1"))
    start()
    pg.wait_for_timeout(1800)
    check(ls("wl-code-v") == str(base_build + FAR + 1), "new version downloaded in the background")
    check("नया संस्करण 3.1 तैयार है" in txt("#scr-now"), "Now screen: ready banner")
    pg.screenshot(path=str(OUT / "u02-ready.png"))
    pg.click("#scr-now >> text=अभी लगाएँ")
    pg.wait_for_selector("#scr-now .card", timeout=8000)
    pg.wait_for_timeout(300)
    check(pg.url.endswith("/index.html?shell=3"), "new version runs through the starter page " + pg.url)
    now = txt("#scr-now")
    check("परीक्षण वाला नया बदलाव 3.1" in now and "संस्करण 3.1" in now, "what's new card shows 3.1 notes")
    check("110 / 134" in now, "list kept after the update")
    check(ls("wl-boot") is None, "new version reported a good start")
    pg.screenshot(path=str(OUT / "u03-updated.png"))
    pg.click("#scr-now .whatsnew >> text=ठीक है")
    check(not pg.is_visible("#scr-now .whatsnew") and ls("wl-seen-build") == str(base_build + FAR + 1), "what's new dismissed")
    pg.click("#tabs .tab >> text=सूची")
    pg.go_back()
    pg.wait_for_timeout(200)
    check(pg.is_visible("#scr-now") and not pg.is_visible("#scr-queue"), "back button works in the updated page")
    pg.click("#scr-now .btn.primary.big")
    check(st()["progress"]["suits"] == {"s": 8, "e": 3}, "episode button saves in the updated page")
    open_settings()
    check("आपका संस्करण 3.1" in txt("#scr-settings") and "ढाँचा 3" in txt("#scr-settings"), "settings shows 3.1, shell still known")

    # Restart offline: the downloaded version still opens.
    remote["offline"] = True
    start()
    check(pg.url.endswith("/index.html?shell=3") and "110 / 134" not in txt("#scr-now") and "111 / 134" in txt("#scr-now"), "offline restart opens 3.1 with saved progress")
    pg.wait_for_timeout(1800)
    open_settings()
    check("इंटरनेट" in txt("#scr-settings") or "जवाब नहीं मिला" in txt("#scr-settings"), "offline: friendly message")
    remote.pop("offline")

    # A page with a syntax error is never stored.
    broken = variant(base_build + FAR + 2, "3.2").replace("function base(id)", "function base(id) {{", 1)
    publish(base_build + FAR + 2, "3.2", broken)
    pg.click("#scr-settings >> text=अभी अपडेट जाँचें")
    pg.wait_for_timeout(800)
    check(ls("wl-code-v") == str(base_build + FAR + 1), "syntax-broken page rejected, 3.1 kept")
    check("सही जवाब नहीं मिला" in txt("#scr-settings"), "rejection shown as an error")

    # A page that crashes on start: stored, fails once, then the starter page falls back.
    crash = variant(base_build + FAR + 3, "3.3", ' throw new Error("test crash");')
    publish(base_build + FAR + 3, "3.3", crash)
    pg.click("#scr-settings >> text=अभी अपडेट जाँचें")
    pg.wait_for_timeout(800)
    check(ls("wl-code-v") == str(base_build + FAR + 3), "crashing page downloaded (syntax is fine)")
    pg.goto(LOADER)
    pg.wait_for_timeout(1200)
    check(not pg.is_visible("#scr-now .card") and ls("wl-boot") == str(base_build + FAR + 3), "crashing page left a failed-start mark")
    start()
    check(pg.url.endswith("/app.html?shell=3") and ls("wl-bad-v") == str(base_build + FAR + 3), "next start falls back to the bundled page")
    check("111 / 134" in txt("#scr-now"), "list safe after the fallback")
    pg.wait_for_timeout(1800)
    check(ls("wl-code") is None, "bad version not downloaded again")
    open_settings()
    check("रोक दिया" in txt("#scr-settings"), "settings explains the blocked version")

    # A version that needs a newer Android shell.
    publish(base_build + FAR + 4, "4.0", variant(base_build + FAR + 4, "4.0"), min_shell=4)
    pg.click("#scr-settings >> text=अभी अपडेट जाँचें")
    pg.wait_for_timeout(800)
    href = pg.get_attribute("#scr-settings a >> text=नया ऐप डाउनलोड करें", "href")
    check(href == LIVE + "watchlist.apk" and ls("wl-code") is None, "needs new APK: link shown, page not stored")
    pg.screenshot(path=str(OUT / "u04-need-apk.png"), full_page=True)

    # A download older than the bundled page is dropped.
    pg.evaluate("b => { localStorage.setItem('wl-code', '<p>old</p>'); localStorage.setItem('wl-code-v', String(b)); }", base_build - 1)
    start()
    check(pg.url.endswith("/app.html?shell=3") and ls("wl-code") is None, "older download dropped, bundled page runs")

    unexpected = [e for e in errors if "test crash" not in e]
    check(not unexpected, "no unexpected JS errors: " + "; ".join(unexpected))
    b.close()
sys.exit(check.done())

"""Series info from (fake) TVmaze: add-screen suggestions and auto-fill, the info section, offline info, exact counts."""
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
    pg.goto(URL)
    pg.evaluate("([k, s]) => { localStorage.clear(); localStorage.setItem(k, JSON.stringify(s)); localStorage.setItem('wl-seen-build', '99'); }", [KEY, FIXTURE])
    pg.goto(URL)

    # ---- Add screen: typing a name brings suggestions with posters ----
    pg.click("#tabs .fab")
    pg.fill("#add-name", "Yellowstone")
    check(wait_for(pg, "document.querySelectorAll('#add-sugg .pick').length === 2"), "typing a name shows suggestions")
    check(pg.locator("#add-sugg .pick img").count() == 2, "suggestions carry poster pictures")
    check("null" not in pg.inner_text("#scr-add"), "no stray text on the add screen")
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT / "i01-add-suggestions.png"))

    # A redraw while typing keeps what was typed.
    pg.fill("#add-why", "परीक्षण वाली वजह")
    pg.evaluate("render()")
    check(pg.input_value("#add-name") == "Yellowstone" and pg.input_value("#add-why") == "परीक्षण वाली वजह", "a redraw keeps the typed form")

    # Picking one links it: channel and exact counts fill in, the manual count boxes hide.
    pg.click("#add-sugg .pick >> nth=0")
    check(wait_for(pg, "document.querySelector('#add-link .linked') && document.querySelector('#add-link').innerText.includes('3 सीज़न ·')"), "picked show: exact episode count shown")
    check(pg.input_value("#add-where") == "Netflix", "channel filled in")
    check(pg.locator("#add-counts").is_hidden(), "manual count boxes hidden while linked")
    check(pg.locator("#add-sugg .pick").count() == 0, "suggestions close after picking")
    check("null" not in pg.inner_text("#scr-add"), "no stray text after picking")
    pg.screenshot(path=str(OUT / "i02-add-linked.png"), full_page=True)

    # "यह नहीं" unlinks and searches again; picking again works.
    pg.click("#add-link >> text=यह नहीं")
    check(pg.locator("#add-counts").is_visible() and pg.input_value("#add-where") == "", "unlinked: count boxes back, auto channel cleared")
    check(wait_for(pg, "document.querySelectorAll('#add-sugg .pick').length === 2"), "unlinked: suggestions come back")
    pg.click("#add-sugg .pick >> nth=0")
    wait_for(pg, "document.querySelector('#add-link').innerText.includes('3 सीज़न ·')")
    pg.click("#scr-add button[type=submit]")
    s = st()
    cid = [k for k, v in s["custom"].items() if v["name"] == "Yellowstone"][0]
    tv = s["tv"].get(cid)
    check(isinstance(tv, int) and tv > 0, "saved linked to the picked show")
    check(s["custom"][cid]["seasons"] == [8 + tv % 3, 10, 10] and s["custom"][cid]["where"] == "Netflix", "saved with exact counts and channel")
    check(s["custom"][cid]["why"] == "परीक्षण वाली वजह", "typed reason saved")
    check(wait_for(pg, f"localStorage.getItem('wl-poster:{tv}') !== null"), "poster stored for the new series")

    # A fresh visit to the add screen starts empty.
    pg.click("#tabs .fab")
    check(pg.input_value("#add-name") == "" and pg.input_value("#add-why") == "", "new visit starts with an empty form")

    # Typing my own counts instead of the internet's.
    pg.fill("#add-name", "Billions")
    wait_for(pg, "document.querySelectorAll('#add-sugg .pick').length > 0")
    pg.click("#add-sugg .pick >> nth=0")
    wait_for(pg, "document.querySelector('#add-link').innerText.includes('सीज़न ·')")
    check("आपकी सूची में पहले से है" in pg.inner_text("#add-link"), "warns when the series is already in the list")
    pg.click("#add-link >> text=गिनती ख़ुद लिखें")
    check(pg.locator("#add-counts").is_visible(), "own counts: count boxes shown")
    pg.fill("#add-seasons", "2"); pg.fill("#add-eps", "5")
    pg.click("#scr-add button[type=submit]")
    s = st()
    bid = [k for k, v in s["custom"].items() if v["name"] == "Billions"][0]
    check(s["custom"][bid]["seasons"] == [5, 5] and s["tv"].get(bid) == 3606, "own counts kept, still linked")

    # No internet: the form still works by hand.
    fake.offline = True
    pg.click("#tabs .fab")
    pg.fill("#add-name", "Some Show")
    check(wait_for(pg, "document.querySelector('#add-sugg').innerText.includes('इंटरनेट नहीं मिला')"), "offline: says suggestions need internet")
    pg.go_back()
    fake.offline = False

    # ---- Detail screen: the info section ----
    calls0 = len(fake.api_calls)
    pg.click("#tabs .tab >> text=अभी")
    pg.click("#scr-now .name-lg")
    check(wait_for(pg, "(document.querySelector('#scr-detail [data-info]') || {}).innerText?.includes('ख़त्म हो चुकी')"), "info section shows the status")
    info = pg.inner_text("#scr-detail [data-info]")
    check("2011 – 2019" in info and "USA" not in info and "Netflix" in info, "years and channel shown")
    check("ड्रामा" in info and "क़ानूनी" in info, "genres shown in Hindi")
    check("9 सीज़न · 134 एपिसोड" in info and "लगभग 45 मिनट" in info and "8.1 / 10" in info, "totals, runtime and rating shown")
    check(pg.locator("#scr-detail [data-info] .panel").count() == 0, "built-in series: no count fixing offered")
    check(pg.get_attribute("#scr-detail [data-info] a", "href").startswith("https://www.tvmaze.com/"), "links to the show on TVmaze")
    pg.screenshot(path=str(OUT / "i03-detail-info.png"), full_page=True)
    check(any(c.startswith("/shows/172?") for c in fake.api_calls[calls0:]), "info fetched with one show call")

    # Opening it again uses the stored info.
    n = len(fake.api_calls)
    pg.go_back(); pg.click("#scr-now .name-lg")
    pg.wait_for_selector("#scr-detail [data-info] .facts")
    pg.wait_for_timeout(500)
    check(not any(c.startswith("/shows/172?") for c in fake.api_calls[n:]), "stored info is not fetched again")

    # A running show: next episode date.
    pg.evaluate("openDetail('hotd')")
    check(wait_for(pg, "(document.querySelector('#scr-detail .next-ep') || {}).innerText?.includes('5 दिन बाद')"), "running show: next episode in 5 days")
    check("अभी चल रही है" in pg.inner_text("#scr-detail [data-info]") and "2011 से अब तक" in pg.inner_text("#scr-detail [data-info]"), "running show: status and years")
    pg.screenshot(path=str(OUT / "i04-running.png"), full_page=True)

    # TVmaze's numbering 1, 3, 4, 5 still counts four seasons.
    pg.evaluate("openDetail('moneyheist')")
    check(wait_for(pg, "(document.querySelector('#scr-detail [data-info]') || {}).innerText?.includes('4 सीज़न · 41 एपिसोड')"), "season numbers with a gap: counted right")

    # Own series with different counts: fix them, and undo.
    pg.evaluate("openDetail('peaky')")
    check(wait_for(pg, "document.querySelector('#scr-detail [data-info] .panel') !== null"), "own series: count fixing offered")
    check("6 सीज़न + फ़िल्म" in pg.inner_text("#scr-detail [data-info] .panel"), "shows what the list has now")
    pg.screenshot(path=str(OUT / "i05-fix-counts.png"), full_page=True)
    pg.click("#scr-detail >> text=सही गिनती लगाएँ")
    s = st()
    check(s["custom"]["peaky"]["seasons"] == [6] * 6 and s["custom"]["peaky"]["epsText"] == "", "exact counts saved")
    check(pg.locator("#scr-detail [data-info] .panel").count() == 0, "offer goes away after fixing")
    pg.click("#snack-undo")
    check(st()["custom"]["peaky"]["seasons"] is None, "undo puts the old count back")

    # A series with no TVmaze match points to the poster picker.
    pg.evaluate("k => { const s = JSON.parse(localStorage.getItem(k)); s.tv.got = 0; localStorage.setItem(k, JSON.stringify(s)); }", KEY)
    pg.goto(URL)
    pg.evaluate("openDetail('got')")
    check("पोस्टर पर दबाकर" in pg.inner_text("#scr-detail [data-info]"), "no poster chosen: says how to link it")

    # Offline: stored info still shows; missing info says it needs internet, and "फिर कोशिश करें" works once online.
    fake.offline = True
    pg.goto(URL)
    pg.evaluate("openDetail('suits')")
    check(pg.locator("#scr-detail [data-info] .facts").count() == 1, "offline: stored info still shows")
    pg.evaluate("openDetail('crown')")
    check(wait_for(pg, "document.querySelector('#scr-detail [data-info]').innerText.includes('इंटरनेट चाहिए')"), "offline: missing info asks for internet")
    fake.offline = False
    pg.click("#scr-detail [data-info] >> text=फिर कोशिश करें")
    check(wait_for(pg, "document.querySelector('#scr-detail [data-info] .facts') !== null"), "retry brings the info")

    # Backup carries the link to TVmaze, not the info itself.
    code = pg.evaluate("backupCode()")
    data = json.loads(base64.b64decode(code[4:]).decode("utf-8"))
    check("wl-info" not in json.dumps(data) and data["tv"].get(cid) == tv, "backup holds the links only")

    # Old saved labels that do not fit are dropped, good ones are kept.
    pg.evaluate("""k => { const s = JSON.parse(localStorage.getItem(k));
      s.custom.peaky.seasons = [6, 6]; s.custom.peaky.labels = ['सीज़न 1', 'सीज़न 3'];
      s.custom.got.seasons = [10]; s.custom.got.labels = ['a', 'b'];
      localStorage.setItem(k, JSON.stringify(s)); }""", KEY)
    pg.goto(URL)
    s = pg.evaluate("state")
    check(s["custom"]["peaky"].get("labels") == ["सीज़न 1", "सीज़न 3"] and "labels" not in s["custom"]["got"], "season labels checked on load")
    check(not errors, "no JS errors: " + "; ".join(errors))
    ctx.close()

    # Tablet sideways: the info section in the right-hand pane.
    ctx = b.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=1.5, is_mobile=True, has_touch=True)
    FakeTVmaze().attach(ctx)
    pg = ctx.new_page()
    pg.goto(URL)
    pg.evaluate("([k, s]) => { localStorage.clear(); localStorage.setItem(k, JSON.stringify(s)); localStorage.setItem('wl-seen-build', '99'); }", [KEY, FIXTURE])
    pg.goto(URL)
    pg.click("#tabs .tab >> text=सूची")
    check(wait_for(pg, "document.querySelector('#scr-detail [data-info] .facts') !== null"), "tablet: info in the side pane")
    pg.wait_for_timeout(1500)
    pg.evaluate("document.getElementById('scr-detail').scrollTop = 420")
    pg.wait_for_timeout(200)
    pg.screenshot(path=str(OUT / "i06-tablet.png"))
    b.close()
sys.exit(check.done())

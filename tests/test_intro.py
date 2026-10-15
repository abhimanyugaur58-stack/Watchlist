"""The owner's signature: the opening screen, skipping it with a tap, the owner card in settings and its on/off switch."""
import sys
import time

from playwright.sync_api import sync_playwright
from common import APP_URL as URL, APP, OUT, KEY, FIXTURE, Checker

check = Checker()


def wait_for(pg, js, timeout=8000):
    t0 = time.time()
    while time.time() - t0 < timeout / 1000:
        if pg.evaluate(js):
            return True
        pg.wait_for_timeout(50)
    return False


GONE = "document.getElementById('intro') === null"

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL)
    pg.evaluate("([k, s]) => { localStorage.clear(); localStorage.setItem(k, JSON.stringify(s)); localStorage.setItem('wl-seen-build', '99'); }", [KEY, FIXTURE])

    # Opens with the signature, which goes away by itself in about a second.
    t0 = time.time()
    pg.goto(URL)
    check(pg.locator("#intro svg path").count() == 1, "opening shows the signature")
    check(pg.evaluate("getComputedStyle(document.getElementById('intro')).color") == "rgb(227, 189, 108)", "signature is gold")
    pg.wait_for_timeout(500)
    pg.screenshot(path=str(OUT / "s01-intro-mid.png"))
    check(wait_for(pg, GONE, 3000), "opening goes away by itself")
    took = time.time() - t0
    check(0.9 < took < 2.5, f"opening lasts about a second ({took:.2f}s)")
    check(pg.is_visible("#scr-now"), "first screen is there underneath")

    # A tap skips it, and the tap does not press what is underneath.
    pg.goto(URL)
    pg.wait_for_timeout(150)
    box = pg.locator("#scr-now .name-lg").bounding_box()
    pg.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    check(wait_for(pg, GONE, 600), "a tap skips the opening")
    check(pg.evaluate("screen") == "now" and pg.is_visible("#scr-now"), "the tap does not open the series underneath")

    # Settings: the owner card.
    pg.click("#scr-now [aria-label^='सेटिंग और बैकअप']")
    card = pg.locator("#scr-settings .owner")
    check(card.count() == 1, "settings has the owner card")
    check(card.locator("svg.sig path").count() == 1, "owner card shows the signature")
    txt = card.inner_text()
    check("इस ऐप के मालिक" in txt and "© 2026 Abhimanyu G." in txt, "owner card names the owner")
    check(pg.get_attribute("#intro-switch", "aria-checked") == "true", "opening switch starts on")
    check(pg.locator("#scr-settings a >> text=TVmaze").count() == 1, "TVmaze credit is still there")
    card.scroll_into_view_if_needed()
    pg.wait_for_timeout(200)
    card.screenshot(path=str(OUT / "s02-owner-card.png"))
    pg.screenshot(path=str(OUT / "s03-settings.png"))

    # Turning it off: the next start has no opening at all.
    pg.click("#intro-switch")
    check(pg.get_attribute("#intro-switch", "aria-checked") == "false", "switch turns off")
    check(pg.evaluate("localStorage.getItem('wl-intro')") == "off", "choice stored on this device")
    pg.goto(URL)
    check(pg.evaluate(GONE), "switched off: no opening on start")
    backup = pg.evaluate("backupCode()")
    check("wl-intro" not in backup, "switch is a device setting, not in the backup")

    # And on again.
    pg.click("#scr-now [aria-label^='सेटिंग और बैकअप']")
    pg.click("#intro-switch")
    pg.goto(URL)
    check(pg.locator("#intro svg").count() == 1, "switched on again: opening is back")
    check(not errors, "no JS errors: " + "; ".join(errors))

    # The page still passes the update check with its two scripts.
    html = APP.read_text(encoding="utf-8")
    check(pg.evaluate("h => codeLooksRunnable(h)", html), "updated page passes the runnable check")
    ctx.close()

    # Reduced motion: no wipe, and it leaves sooner.
    ctx = b.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce", is_mobile=True, has_touch=True)
    pg = ctx.new_page()
    pg.goto(URL)
    t0 = time.time()
    pg.goto(URL)
    check(pg.evaluate("getComputedStyle(document.querySelector('#intro svg')).animationName") == "none", "reduced motion: no wipe")
    check(wait_for(pg, GONE, 2000) and time.time() - t0 < 1.6, "reduced motion: leaves quickly")
    ctx.close()

    # Tablet sideways: the opening is centred and not too big.
    ctx = b.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=1.5, is_mobile=True, has_touch=True)
    pg = ctx.new_page()
    pg.goto(URL)
    pg.goto(URL)
    w = pg.evaluate("document.querySelector('#intro svg').getBoundingClientRect().width")
    check(400 <= w <= 441, f"tablet: signature width {w:.0f}px")
    pg.wait_for_timeout(1000)
    pg.screenshot(path=str(OUT / "s04-intro-tablet.png"))
    b.close()
sys.exit(check.done())

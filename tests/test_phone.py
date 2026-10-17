import json, sys
from playwright.sync_api import sync_playwright
from common import APP_URL as URL, OUT, VERSION, FIXTURE, load_fixture, Checker, FakeTVmaze, NO_INTRO
SHOTS = str(OUT) + "/"
check = Checker()

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    ctx.add_init_script(NO_INTRO)
    FakeTVmaze().attach(ctx)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
    load_fixture(pg)
    st = lambda: pg.evaluate("JSON.parse(localStorage.getItem('abhimanyu-watchlist-v2'))")
    txt = lambda sel: pg.inner_text(sel)

    # ---- Fresh install
    now = txt("#scr-now")
    check("Suits" in now and "110 / 134" in now and "24 बाकी" in now, "fresh: Suits at 110/134, 24 left")
    check("सीज़न 8 · एपिसोड 2 पूरा" in now, "fresh: position text S8E2")
    check("अगला: सीज़न 8, एपिसोड 3" in now, "fresh: next episode text")
    check("House of Cards" in now and "The Crown" in now, "fresh: up next shows HoC and Crown")
    pg.screenshot(path=SHOTS + "01-now.png")

    # plus ep 14 times -> S8E16, once more -> S9E1
    for i in range(14): pg.click("#scr-now .btn.primary.big")
    s = st(); check(s["progress"]["suits"] == {"s": 8, "e": 16}, "plus x14 -> S8E16 " + str(s["progress"]["suits"]))
    pg.click("#scr-now .btn.primary.big")
    s = st(); check(s["progress"]["suits"] == {"s": 9, "e": 1}, "plus -> S9E1 " + str(s["progress"]["suits"]))
    check("सीज़न 9, एपिसोड 1 देखा" in txt("#snack"), "snack shows episode")
    pg.click("#snack-undo")
    s = st(); check(s["progress"]["suits"] == {"s": 8, "e": 16}, "undo -> back to S8E16")
    for i in range(9): pg.click("#scr-now .btn.primary.big")
    s = st(); check(s["progress"]["suits"] == {"s": 9, "e": 9}, "-> S9E9")
    pg.click("#scr-now .btn.primary.big")
    now = txt("#scr-now")
    check("पूरी सीरीज़ देख ली ✓" in now and "134 / 134" in now, "at end: finish button shows, 134/134")
    pg.screenshot(path=SHOTS + "02-now-end.png")
    pg.click("text=पूरी सीरीज़ देख ली ✓")
    check(pg.is_visible("#scr-finished"), "finish -> finished tab")
    fin = txt("#scr-finished")
    check("Suits को 10 में से कितने?" in fin, "rating prompt is for Suits")
    pg.screenshot(path=SHOTS + "03-finished.png")
    # Type note, then pick score: note must survive
    pg.fill("#pending-note", "हार्वी की वफ़ादारी")
    pg.click("#scr-finished .score >> text=9")
    check(pg.input_value("#pending-note") == "हार्वी की वफ़ादारी", "note survives picking a score")
    pg.click("#scr-finished >> text=सेव करें")
    s = st(); check(s["ratings"].get("suits") == 9 and s["notes"].get("suits") == "हार्वी की वफ़ादारी", "rating + note saved")
    fin = txt("#scr-finished")
    check("Peaky Blinders को 10 में से कितने?" in fin, "next pending is Peaky")
    check("9 / 10" in fin, "diary shows Suits 9/10")
    # Now screen should show HoC S3
    pg.click("nav#tabs >> text=अभी")
    now = txt("#scr-now")
    check("House of Cards" in now and "सीज़न 3 शुरू करना है" in now and "26 / 73" in now, "now shows HoC S3 start, 26/73")
    check(pg.evaluate("history.state.d") == 0, "back at depth 0 on अभी")

    # ---- Navigation depth
    pg.click("nav#tabs >> text=सूची")
    check(pg.evaluate("history.state.d") == 1, "queue depth 1")
    pg.click("nav#tabs >> text=देख लीं")
    check(pg.evaluate("history.state.d") == 1, "finished replaces at depth 1")
    pg.click("nav#tabs >> text=सूची")
    pg.click("#scr-queue .qrow >> text=The Crown")
    check(pg.is_visible("#scr-detail") and pg.evaluate("history.state.d") == 2, "detail at depth 2")
    pg.screenshot(path=SHOTS + "04-detail-crown.png")
    pg.go_back(); pg.wait_for_timeout(100)
    check(pg.is_visible("#scr-queue"), "back -> queue")
    pg.go_back(); pg.wait_for_timeout(100)
    check(pg.is_visible("#scr-now"), "back -> now")
    pg.screenshot(path=SHOTS + "05-queue-check.png")

    # Detail of Suits (done) and back
    pg.click("nav#tabs >> text=सूची")
    pg.screenshot(path=SHOTS + "06-queue.png", full_page=False)
    q = txt("#scr-queue")
    check("1 / 19 पूरी" in q, "queue header 1/19 (two series joined in 3.6, five in 3.7)")
    pg.click("#scr-queue .fchip >> text=JioHotstar")
    q = txt("#scr-queue")
    check("Succession" in q and "Narcos" not in q, "JioHotstar filter")
    pg.click("#scr-queue .fchip >> text=सभी")

    # Detail tracker on Vikings: season pick + minus across boundary
    pg.click("#scr-queue .qrow >> text=Vikings")
    pg.click("#scr-detail .schip >> text=S4")
    s = st(); check(s["progress"]["vikings"] == {"s": 4, "e": 0}, "pick S4 -> S4E0")
    pg.click("#scr-detail [aria-label='एक एपिसोड कम']")
    s = st(); check(s["progress"]["vikings"] == {"s": 3, "e": 9}, "minus from S4E0 -> S3E9 " + str(s["progress"]["vikings"]))
    pg.click("#scr-detail [aria-label='एक एपिसोड और देखा']")
    pg.click("#scr-detail [aria-label='एक एपिसोड और देखा']")
    s = st(); check(s["progress"]["vikings"] == {"s": 4, "e": 1}, "plus x2 -> S4E1 " + str(s["progress"]["vikings"]))
    # Add a character and a scene note
    pg.click("#scr-detail >> text=+ किरदार")
    pg.fill("#char-name", "रैगनार")
    pg.select_option("#char-type", "0")
    pg.click("#scr-detail .panel >> text=जोड़ें")
    s = st(); check(s["chars"].get("vikings") == [{"n": "रैगनार", "t": 0}], "character added")
    pg.click("#scr-detail >> text=+ नोट")
    pg.fill("#scene-text", "रैगनार की चुप्पी वाला सीन")
    pg.click("#scr-detail .panel >> text=जोड़ें")
    s = st(); check(len(s["scenes"].get("vikings", [])) == 1 and s["scenes"]["vikings"][0]["l"] == "सीज़न 4, एपिसोड 1", "scene note added with label " + str(s["scenes"].get("vikings")))
    pg.screenshot(path=SHOTS + "07-detail-vikings.png", full_page=True)
    # Move Vikings to first
    pg.click("#detail-actions >> text=जगह बदलें")
    pg.select_option("#place-vikings", "main:0")
    pg.click("#scr-detail .panel button.primary")
    s = st(); check(s["layout"]["main"][0] == "vikings", "moved Vikings to first")
    pg.click("#snack-undo")
    s = st(); check(s["layout"]["main"].index("vikings") == 11, "undo move (3.7 order: Vikings is 12th)")
    # Hindi change
    pg.click("#detail-actions >> text=हिंदी बदलें")
    pg.select_option("#hindi-vikings", "check")
    pg.click("#scr-detail .panel >> text=सेव करें")
    s = st(); check(s["hindi"].get("vikings") == "check", "hindi override saved")
    # Delete
    pg.click("#detail-actions >> text=हटाएँ")
    pg.click("#scr-detail >> text=हाँ, हटाएँ")
    pg.wait_for_timeout(150)
    s = st(); check("vikings" not in s["layout"]["main"] and "vikings" in s["removed"], "Vikings removed")
    check(pg.is_visible("#scr-queue"), "after delete -> back to queue")
    check("vikings" not in s["layout"]["main"], "not in main")

    # ---- Add series from FAB on queue
    pg.click("nav#tabs .fab")
    check(pg.is_visible("#scr-add"), "FAB -> add")
    pg.screenshot(path=SHOTS + "08-add.png")
    pg.click("#scr-add button[type=submit]")
    check(pg.is_visible("#scr-add .err"), "empty name error")
    pg.fill("#add-name", "Yellowstone")
    pg.fill("#add-where", "JioHotstar")
    pg.fill("#add-seasons", "5")
    pg.fill("#add-eps", "10")
    pg.select_option("#add-place", "main:hoc")
    pg.click("#scr-add button[type=submit]")
    pg.wait_for_timeout(150)
    s = st()
    cid = [k for k, v in s["custom"].items() if v["name"] == "Yellowstone"]
    check(len(cid) == 1 and s["layout"]["main"][s["layout"]["main"].index("hoc") + 1] == cid[0], "added after HoC")
    check(pg.is_visible("#scr-queue") and pg.evaluate("history.state.d") == 1, "after add -> queue at depth 1")
    check(s["custom"][cid[0]]["seasons"] == [10] * 5, "custom seasons array")

    # ---- Settings: pace, backup, restore removed
    pg.click("nav#tabs >> text=अभी")
    pg.click("#scr-now [aria-label^='सेटिंग और बैकअप']")
    check(pg.is_visible("#scr-settings"), "settings opens")
    pg.click("#scr-settings .fchip >> text=2 एपिसोड")
    s = st(); check(s["pace"] == 2, "pace saved")
    pg.click("#scr-settings >> text=हटाई गई सीरीज़ वापस लाएँ (1)")
    s = st(); check("vikings" in s["layout"]["main"] and s["removed"] == [], "removed restored")
    pg.click("#scr-settings >> text=बैकअप कोड कॉपी करें")
    pg.wait_for_timeout(200)
    code = pg.input_value("#backup-out")
    check(code.startswith("WL2:"), "backup code generated")
    href = pg.get_attribute("#scr-settings a[href^='whatsapp']", "href")
    check(href.startswith("whatsapp://send?text=WL2"), "whatsapp link")
    st_txt = txt("#scr-settings")
    check(("आपका संस्करण " + VERSION) in st_txt and "इंटरनेट पर खुला संस्करण" in st_txt, "update card in a plain browser")
    pg.screenshot(path=SHOTS + "09-settings.png", full_page=True)
    before = st()
    # wipe and restore
    pg.evaluate("localStorage.clear()"); pg.reload()
    s = st(); check(s["custom"] == {} or "Yellowstone" not in json.dumps(s), "wiped")
    pg.click("#scr-now [aria-label^='सेटिंग और बैकअप']")
    pg.fill("#restore-code", "garbage")
    pg.click("#scr-settings >> text=सूची वापस लाएँ")
    check(pg.is_visible("#scr-settings .err") and pg.input_value("#restore-code") == "garbage", "bad code error, draft kept")
    pg.fill("#restore-code", code)
    pg.click("#scr-settings >> text=सूची वापस लाएँ")
    pg.click("#scr-settings >> text=हाँ, वापस लाएँ")
    after = st()
    check(after == before, "restore round-trip equal")
    pg.reload()
    check(st() == before, "idempotent after reload")

    # ---- Back from settings
    pg.go_back(); pg.wait_for_timeout(100)
    check(pg.is_visible("#scr-now"), "back from settings -> now")

    check(not errors, "no JS errors: " + "; ".join(errors))

    # ---- Migration from v1.1 state
    v11 = {"done": ["gentlemen"], "custom": {"c1": {"name": "Billions 2", "where": "Prime", "eps": "7 सीज़न · 84 एपिसोड", "hindi": "check", "why": "x"}},
           "removed": ["ozark"], "hindi": {"diplomat": "ok"},
           "layout": {"main": ["suits", "hoc", "crown", "diplomat", "succession", "narcos", "lincoln", "vikings", "moneyheist", "guinness", "hotd", "c1"], "break": ["gentlemen"], "maybe": ["billions", "bcs", "narcosmx", "designated"]}}
    pg.evaluate("s => { localStorage.clear(); localStorage.setItem('abhimanyu-watchlist-v2', JSON.stringify(s)); }", v11)
    pg.reload()
    s = st()
    check(s["layout"]["main"][-1] == "c1" and s["custom"]["c1"]["epsText"] == "7 सीज़न · 84 एपिसोड", "v1.1 custom kept with eps text")
    check("ozark" not in json.dumps(s["layout"]) and s["removed"] == ["ozark"], "v1.1 removed stays removed")
    check(s["hindi"]["diplomat"] == "ok" and "gentlemen" in s["done"], "v1.1 hindi + done kept")
    check(s["layout"]["archive"] == [] and "suits" not in s["progress"], "v1.1: no sample data added")
    pg.click("nav#tabs >> text=सूची")
    q = txt("#scr-queue")
    check("Billions 2" in q and "7 सीज़न · 84 एपिसोड" in q, "v1.1 custom shown")
    pg.click("nav#tabs >> text=देख लीं")
    f = txt("#scr-finished")
    check("The Gentlemen" in f and "Peaky" not in f, "diary has gentlemen only")
    pg.screenshot(path=SHOTS + "10-finished-migrated.png", full_page=True)

    # ---- 3.5: Ozark (Hindi found) leaves "हिंदी मिले तो देखें". 3.6 then sets the new middle of the main order, once:
    # The Diplomat → Queenmaker → Succession → Ozark → Vincenzo → Narcos
    # (3.7 put Ginny & Georgia between Narcos and The Lincoln Lawyer.)
    NEW_MID = ["diplomat", "queenmaker", "succession", "ozark", "vincenzo", "narcos", "ginny", "lincoln"]
    def saved(s):
        pg.evaluate("s => { localStorage.clear(); localStorage.setItem('abhimanyu-watchlist-v2', JSON.stringify(s)); }", s)
        pg.reload()
        return st()
    def in_order(m, ids):
        if not all(i in m for i in ids): return False
        a = m.index(ids[0])
        return [m.index(i) for i in ids] == list(range(a, a + len(ids)))
    old34 = json.loads(json.dumps(FIXTURE)); old34["hindi"] = {"ozark": "likely", "succession": "check"}
    s = saved(old34)
    m = s["layout"]["main"]
    check("ozark" not in s["layout"]["maybe"] and in_order(m, NEW_MID), "3.6: saved 3.4 list gets the new middle " + str(m))
    check(len(m) == 19 and m[-1] == "rop" and m[:4] == ["suits", "hoc", "crown", "diplomat"], "3.6: new series are not left at the end " + str(m))
    check({"ozark-hindi", "order-oct16"} <= set(s["migs"]) and "ozark" not in s["hindi"] and "succession" not in s["hindi"],
          "3.6: both moves marked done, old Hindi marks on Ozark and Succession cleared")

    old35 = json.loads(json.dumps(FIXTURE)); old35["migs"] = ["ozark-hindi"]
    old35["layout"]["maybe"].remove("ozark")
    old35["layout"]["main"] = ["suits", "hoc", "crown", "diplomat", "succession", "narcos", "ozark", "lincoln", "vikings", "moneyheist", "guinness", "hotd"]
    s = saved(old35)
    m = s["layout"]["main"]
    check(in_order(m, NEW_MID) and len(m) == 19, "3.6: saved 3.5 list (Ozark after Narcos) gets the new middle " + str(m))

    pg.click("nav#tabs >> text=सूची")
    q = txt("#scr-queue")
    main_part = q.split("छोटा ब्रेक")[0]
    names = ["The Diplomat", "Queenmaker", "Succession", "Ozark", "Vincenzo", "Narcos", "The Lincoln Lawyer"]
    check(all(n in main_part for n in names) and [main_part.index(n) for n in names] == sorted(main_part.index(n) for n in names),
          "3.6: list shows Diplomat, Queenmaker, Succession, Ozark, Vincenzo, Narcos in order")
    pg.screenshot(path=SHOTS + "11-queue-3.6.png", full_page=True)
    for name, hindi, where in [("Queenmaker", "हिंदी ✓", "Netflix"), ("Vincenzo", "हिंदी ✓", "Netflix"),
                               ("Ozark", "हिंदी ✓ (आपने देखा)", "Netflix"), ("Succession", "हिंदी ✓ (आपने देखा)", "JioHotstar")]:
        pg.click("#scr-queue .qrow >> text=" + name)
        d = txt("#scr-detail")
        check(hindi in d and "हिंदी जाँचें" not in d and where in d, "3.6: " + name + " detail shows " + hindi + " on " + where)
        if name == "Queenmaker": pg.screenshot(path=SHOTS + "12-queenmaker-detail.png", full_page=True)
        pg.go_back(); pg.wait_for_timeout(100)

    moved_back = json.loads(json.dumps(s)); moved_back["layout"]["main"].remove("ozark"); moved_back["layout"]["maybe"].append("ozark")
    moved_back["layout"]["main"].remove("queenmaker"); moved_back["layout"]["break"].append("queenmaker")
    s = saved(moved_back)
    check("ozark" in s["layout"]["maybe"] and "ozark" not in s["layout"]["main"] and "queenmaker" in s["layout"]["break"],
          "3.6: a later move by hand stays")

    no_narcos = json.loads(json.dumps(FIXTURE)); no_narcos["layout"]["main"].remove("narcos"); no_narcos["removed"] = ["narcos"]
    m = saved(no_narcos)["layout"]["main"]
    check(in_order(m, ["diplomat", "queenmaker", "succession", "ozark", "vincenzo", "ginny", "lincoln"]) and "narcos" not in m,
          "3.6/3.7: Narcos deleted -> Vincenzo, then Ginny & Georgia before The Lincoln Lawyer " + str(m))

    finished = json.loads(json.dumps(FIXTURE)); finished["done"].append("succession")
    finished["layout"]["main"].remove("succession"); finished["layout"]["archive"].append("succession")
    s = saved(finished); m = s["layout"]["main"]
    check("succession" in s["layout"]["archive"] and "succession" not in m and in_order(m, ["diplomat", "queenmaker", "ozark", "vincenzo", "narcos"]),
          "3.6: a finished Succession stays in the diary list " + str(m))

    # ---- 3.7: five series with Hindi audio join the main order where he chose, once.
    ORDER37 = ["suits", "hoc", "crown", "diplomat", "queenmaker", "succession", "ozark", "vincenzo", "narcos", "ginny", "lincoln", "vikings",
               "valhalla", "moneyheist", "witcher", "guinness", "hotd", "outerbanks", "rop"]
    old36 = json.loads(json.dumps(FIXTURE)); old36["migs"] = ["ozark-hindi", "order-oct16"]
    old36["layout"]["maybe"].remove("ozark")
    old36["layout"]["main"] = ["suits", "hoc", "crown", "diplomat", "queenmaker", "succession", "ozark", "vincenzo", "narcos", "lincoln",
                               "vikings", "moneyheist", "guinness", "hotd"]
    s = saved(old36); m = s["layout"]["main"]
    check(m == ORDER37, "3.7: saved 3.6 list gets the five in their places " + str(m))
    check("add-five-oct17" in s["migs"] and s["removed"] == [], "3.7: move marked done, nothing removed")

    with_own = json.loads(json.dumps(old36)); with_own["custom"]["c9"] = {"name": "outer banks", "where": "Netflix", "hindi": "ok", "why": "", "seasons": [10] * 5}
    with_own["layout"]["main"].append("c9"); with_own["progress"]["c9"] = {"s": 2, "e": 3}
    s = saved(with_own); m = s["layout"]["main"]
    check("outerbanks" not in json.dumps(s["layout"]) and "outerbanks" in s["removed"] and "c9" in m and s["progress"]["c9"] == {"s": 2, "e": 3},
          "3.7: his own Outer Banks is kept, the built-in copy left out " + str(m))
    check(in_order(m, ["hotd", "rop"]) and m[-1] == "c9" and in_order(m, ["narcos", "ginny", "lincoln"]) and in_order(m, ["moneyheist", "witcher"]),
          "3.7: the other four placed, his own series keeps its place at the end " + str(m))
    s = saved(s)
    check("outerbanks" not in json.dumps(s["layout"]) and s["layout"]["main"].count("c9") == 1, "3.7: no duplicate after a reload")

    no_vikings = json.loads(json.dumps(old36)); no_vikings["layout"]["main"].remove("vikings"); no_vikings["removed"] = ["vikings"]
    m = saved(no_vikings)["layout"]["main"]
    check("vikings" not in m and in_order(m, ["lincoln", "valhalla", "moneyheist", "witcher", "guinness"]),
          "3.7: Vikings deleted -> Valhalla before Money Heist " + str(m))

    s = saved(old36)
    pg.click("nav#tabs >> text=सूची")
    rows = pg.eval_on_selector_all("#scr-queue .qrow", "els => els.map(e => (e.querySelector('.col > span') || e).textContent.trim())")
    names = ["Narcos", "Ginny & Georgia", "The Lincoln Lawyer", "Vikings", "Vikings: Valhalla", "Money Heist", "The Witcher",
             "House of Guinness", "House of the Dragon", "Outer Banks", "The Rings of Power"]
    pos = [rows.index(n) if n in rows else -1 for n in names]
    check(all(p >= 0 for p in pos) and pos == sorted(pos) and pos[-1] - pos[0] == len(names) - 1, "3.7: list shows the new order " + str(rows))
    pg.screenshot(path=SHOTS + "13-queue-3.7.png", full_page=True)
    for name, where in [("Ginny & Georgia", "Netflix"), ("Vikings: Valhalla", "Netflix"), ("The Witcher", "Netflix"), ("Outer Banks", "Netflix"),
                        ("The Rings of Power", "Prime Video")]:
        pg.click("#scr-queue .qrow >> text=" + name)
        d = txt("#scr-detail")
        check("हिंदी ✓" in d and "हिंदी जाँचें" not in d and where in d, "3.7: " + name + " detail shows हिंदी ✓ on " + where)
        if name == "Ginny & Georgia": pg.screenshot(path=SHOTS + "14-ginny-detail.png", full_page=True)
        pg.go_back(); pg.wait_for_timeout(100)

    hand = json.loads(json.dumps(s)); hand["layout"]["main"].remove("witcher"); hand["layout"]["break"].append("witcher")
    s = saved(hand)
    check("witcher" in s["layout"]["break"] and "witcher" not in s["layout"]["main"], "3.7: a later move by hand stays")

    pg.evaluate("() => localStorage.clear()"); pg.reload()
    s = st(); m = s["layout"]["main"]
    check(m == ORDER37 and "ozark" not in s["layout"]["maybe"], "3.6/3.7: fresh install has the new order " + str(m))
    check(not errors, "no JS errors after order checks: " + "; ".join(errors))

    # ---- Migration from v1.0 key
    pg.evaluate("() => { localStorage.clear(); localStorage.setItem('abhimanyu-watchlist-done', JSON.stringify(['suits'])); }")
    pg.reload()
    s = st()
    check("suits" in s["done"] and s["seeded2"], "v1.0 ticks carried")
    now = txt("#scr-now")
    check("House of Cards" in now, "v1.0: Suits done so now shows HoC")
    check(not errors, "no JS errors at end: " + "; ".join(errors))
    b.close()
sys.exit(check.done())

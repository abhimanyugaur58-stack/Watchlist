"""Shared bits for the browser tests (Playwright + Chromium)."""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
APP = REPO / "docs" / "app.html"
APP_URL = APP.as_uri()
VERSION = re.search(r'const VERSION = "([^"]+)";', APP.read_text(encoding="utf-8")).group(1)
OUT = REPO / "test-out"
OUT.mkdir(exist_ok=True)
KEY = "abhimanyu-watchlist-v2"

# A made-up but realistic saved list: in Suits season 8, House of Cards from season 3, two older series in the diary.
FIXTURE = {
    "done": ["peaky", "got"],
    "custom": {
        "peaky": {"name": "Peaky Blinders", "where": "Netflix", "hindi": "ok", "why": "", "epsText": "6 सीज़न + फ़िल्म", "seasons": None},
        "got": {"name": "Game of Thrones", "where": "JioHotstar", "hindi": "ok", "why": "", "epsText": "8 सीज़न", "seasons": None},
    },
    "progress": {"suits": {"s": 8, "e": 2}, "hoc": {"s": 3, "e": 0}},
    "notes": {"peaky": "परीक्षण वाली राय", "got": "परीक्षण वाली दूसरी राय"},
    "chars": {"peaky": [{"n": "किरदार क", "t": 0}, {"n": "किरदार ख", "t": 1}], "got": [{"n": "किरदार ग", "t": 0}], "suits": [{"n": "किरदार घ", "t": 0}]},
    "layout": {
        "main": ["suits", "hoc", "crown", "diplomat", "succession", "narcos", "lincoln", "vikings", "moneyheist", "guinness", "hotd"],
        "break": ["gentlemen"],
        "maybe": ["billions", "bcs", "narcosmx", "designated", "ozark"],
        "archive": ["peaky", "got"],
    },
    "seeded2": True,
}


def load_fixture(page, url=APP_URL):
    page.goto(url)
    page.evaluate("([k, s]) => { localStorage.clear(); localStorage.setItem(k, JSON.stringify(s)); }", [KEY, FIXTURE])
    page.goto(url)


class Checker:
    def __init__(self):
        self.fails = []
        self.passes = 0

    def __call__(self, cond, msg):
        print(("PASS " if cond else "FAIL ") + msg)
        if cond:
            self.passes += 1
        else:
            self.fails.append(msg)

    def done(self):
        print("PASSES:", self.passes, "FAILS:", len(self.fails))
        return 1 if self.fails else 0


# ---------- Fake TVmaze (the real one is not reachable from test machines) ----------
import io
from urllib.parse import urlparse, parse_qs

TV_NAMES = {172: "Suits", 175: "House of Cards", 3594: "The Crown", 60213: "The Diplomat", 23470: "Succession", 2705: "Narcos",
            52910: "The Lincoln Lawyer", 29: "Vikings", 27436: "La Casa de Papel", 75496: "House of Guinness", 44778: "House of the Dragon",
            64992: "The Gentlemen", 3606: "Billions", 618: "Better Call Saul", 37787: "Narcos: Mexico", 8167: "Designated Survivor",
            13417: "Ozark", 269: "Peaky Blinders", 82: "Game of Thrones", 169: "Breaking Bad"}
PALETTE = [(36, 60, 110), (92, 52, 40), (40, 84, 76), (88, 44, 70), (70, 76, 40), (48, 48, 92), (100, 70, 30)]


def stand_in_poster(tv, name):
    """A plain stand-in poster: colour wash plus the show's name. Real posters come from TVmaze on the phone."""
    from PIL import Image, ImageDraw, ImageFont
    w, h = 210, 295
    top = PALETTE[tv % len(PALETTE)]
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(c * (1 - t) + 12 * t) for c in top))
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 22)
    words, lines, cur = name.upper().split(), [], ""
    for wd in words:
        test = (cur + " " + wd).strip()
        if d.textlength(test, font=font) > w - 24 and cur:
            lines.append(cur); cur = wd
        else:
            cur = test
    lines.append(cur)
    y = h - 30 - 28 * len(lines)
    for ln in lines:
        d.text(((w - d.textlength(ln, font=font)) / 2, y), ln, font=font, fill=(240, 236, 226)); y += 28
    d.rectangle([w // 2 - 18, 40, w // 2 + 18, 42], fill=(212, 166, 74))
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


class FakeTVmaze:
    def __init__(self):
        self.offline = False
        self.api_calls = []
        self.img_calls = []
        self._img = {}

    def attach(self, ctx):
        ctx.route("https://api.tvmaze.com/**", self._api)
        ctx.route("https://static.tvmaze.com/**", self._image)

    @staticmethod
    def _show(tv, name, year="2015"):
        return {"id": tv, "name": name, "premiered": year + "-01-01", "network": {"name": "Netflix"},
                "image": {"medium": f"https://static.tvmaze.com/fake/{tv}.jpg", "original": f"https://static.tvmaze.com/fake/{tv}.jpg"}}

    def _api(self, route):
        if self.offline:
            return route.abort()
        u = urlparse(route.request.url)
        self.api_calls.append(u.path + ("?" + u.query if u.query else ""))
        hdr = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"}
        if u.path.startswith("/shows/"):
            tv = int(u.path.split("/")[2])
            return route.fulfill(status=200, headers=hdr, body=json.dumps(self._show(tv, TV_NAMES.get(tv, f"Show {tv}"))))
        if u.path == "/search/shows":
            q = parse_qs(u.query).get("q", [""])[0].strip()
            exact = [tv for tv, n in TV_NAMES.items() if n.lower() == q.lower()]
            tv = exact[0] if exact else 90000 + sum(map(ord, q.lower())) % 9000
            TV_NAMES.setdefault(tv, q.title())
            decoy = tv + 500000
            TV_NAMES.setdefault(decoy, TV_NAMES[tv] + " LA")
            res = [{"score": 0.9, "show": self._show(tv, TV_NAMES[tv], "2011")}, {"score": 0.5, "show": self._show(decoy, TV_NAMES[decoy], "2025")}]
            return route.fulfill(status=200, headers=hdr, body=json.dumps(res))
        return route.fulfill(status=404, headers=hdr, body="{}")

    def _image(self, route):
        if self.offline:
            return route.abort()
        tv = int(urlparse(route.request.url).path.rsplit("/", 1)[1].split(".")[0])
        self.img_calls.append(tv)
        if tv not in self._img:
            self._img[tv] = stand_in_poster(tv, TV_NAMES.get(tv, f"Show {tv}"))
        route.fulfill(status=200, headers={"Access-Control-Allow-Origin": "*", "Content-Type": "image/jpeg"}, body=self._img[tv])

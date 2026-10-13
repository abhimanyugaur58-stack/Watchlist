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

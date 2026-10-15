# Watchlist app — notes for Claude

## Who this is for

The owner is Abhimanyu. He speaks Hindi and does not read English, usually writes by voice typing on his phone, and uses the app on both a phone and a tablet. Reply to him in simple Hindi. Keep English to button names he has to tap. He is not a developer, so do the git, build and test work yourself and tell him only what changed for him.

## How the app is put together

- `docs/app.html` is the whole app: one self-contained HTML page with the markup, CSS and JS. It is the only place features are written.
- GitHub Pages serves `docs/` at `https://abhimanyugaur58-stack.github.io/Watchlist/`.
- The Android app (`android/`, an Apktool project) is a thin WebView shell. `MainActivity.smali` loads `file:///android_asset/index.html`, the starter page.
  - The starter page runs the newest app page the device has downloaded (kept in localStorage under `wl-code` / `wl-code-v`), or else the bundled `assets/app.html`.
  - A downloaded page that never reaches its first screen (`wl-boot` still set on the next start) is dropped and marked `wl-bad-v`.
  - `Client.smali` keeps `file:` pages inside the WebView and opens every other link (WhatsApp, GitHub, Drive) in its own app.
- `app.html` checks `docs/version.json` about 1 s after it opens. If `build` is higher than its own `BUILD`, and `minShell` is at most the running shell (`window.WL_SHELL`), it downloads `docs/app.html`, checks that it compiles, stores it, and shows "अभी लगाएँ". It also loads on the next start.
- Posters come from TVmaze (free, no key, CC BY-SA; credited in settings). Built-in series use fixed ids in `TV_IDS` (picked by hand: "Suits" alone has five shows on TVmaze). Series he adds himself are matched only on an exact name, and he can pick another poster by tapping the poster on the detail screen; choices live in `state.tv` (0 = no poster). Images are shrunk and stored in localStorage as `wl-poster:<tvmaze id>`. They are not part of the backup code.
- Series info also comes from TVmaze: one call per show, `shows/:id?embed[]=episodes&embed[]=nextepisode`, kept in localStorage as `wl-info:<tvmaze id>` and refreshed after three days. Episode counts come from the episode list (regular episodes only, grouped by season); when TVmaze skips a season number (La Casa de Papel: 1, 3, 4, 5) the counts get `labels`. The detail screen shows it in "जानकारी" (`infoSection`), and offers "सही गिनती लगाएँ" on his own series when the counts differ. Not part of the backup code.
- The add screen searches TVmaze while he types (550 ms pause, `addSearch`). Picking a result links the series (`state.tv`) and fills the channel and exact counts. The form keeps what was typed in `ui.add`, so a redraw loses nothing; the FAB and the "नई सीरीज़ जोड़ें" button start a fresh one.
- The owner's signature (traced from his photo, `brand/signature-*.svg`) is inlined in `app.html` as `SIG_VB` / `SIG_D` in a small first script, which also fills the opening screen `#intro` before anything else draws. `startIntro()` removes it after about 1.25 s, or at once on a tap (the tap never reaches the screen below). Settings has the "इस ऐप के मालिक" card with an on/off switch, stored per device as `wl-intro` ("off"/"on"), not in the backup. Checks other than `tests/test_intro.py` switch the opening off with `ctx.add_init_script(NO_INTRO)`; do the same in any new test context.
- All user data stays on the device in localStorage under the key `abhimanyu-watchlist-v2`. Phone and tablet are separate. The backup code (`WL2:` + base64 JSON) moves data between them.
- The repo is public. Never commit personal data such as his notes or real progress. Test fixtures use made-up values.

## Shipping a live update (the normal case)

1. Edit `docs/app.html`.
2. Bump `const VERSION` (for example "3.1") and `const BUILD` (+1). Add `CHANGES[BUILD]` with one to three short Hindi lines; this is what he sees in "क्या नया है".
3. Set `docs/version.json` to the same `build` and `version`. Leave `minShell` alone unless the page needs a newer shell.
4. Never break saved data:
   - Keep `KEY`, the `WL2:` backup format and `loadState()` able to read every older state.
   - Add migrations rather than renaming fields.
5. Run `tests/run_all.sh`, which uses Python Playwright with Chromium. Update or add checks for the change. Every check must pass.
6. Commit and push to `main`. Pages redeploys in about a minute. Confirm by reading `https://abhimanyugaur58-stack.github.io/Watchlist/version.json` with the web-fetch tool (the session shell may not be allowed to reach github.io).
7. Tell him in Hindi what changed. The phone and tablet pick it up the next time the app opens; "सेटिंग → अभी अपडेट जाँचें" forces a check.

## When a new APK is needed (rare)

Only for shell changes: permissions, icon, app name, or native code in `smali/`. Also when the bundled copy should catch up.

1. Change `android/`.
2. If the starter page or native behaviour changed, bump `var SHELL` in `android/assets/index.html`.
3. Set `var BUNDLED` to the current `BUILD`.
4. Bump `versionCode` (+1) and `versionName` in `android/apktool.yml`.
5. Run `tools/build.sh`. It copies `docs/app.html` into the APK, builds with Apktool 2.10.0, and signs with `android/signing/debug.keystore` (alias `androiddebugkey`, password `android`). It refuses to finish if the certificate SHA-256 is not `1e08a903aef9c3a721510b64ec764d01d3d094eb954161b62544ea8f187b5953`.
   - Android only installs an update over the old app when the key matches. A different key means he has to uninstall, and that wipes his data.
6. Copy `dist/watchlist.apk` to `docs/watchlist.apk` and commit it. Pages serves it at `https://abhimanyugaur58-stack.github.io/Watchlist/watchlist.apk`, which is where the app's "नया ऐप डाउनलोड करें" button points. (Creating GitHub releases is blocked from Claude sessions, so releases are not used.) Also send the APK in chat.
7. If live pages now need the new shell, set `minShell` in `docs/version.json`, so older phones are told to install the APK instead of downloading a page they can't run.
8. Remind him to copy a backup code before installing, and to install over the old app without uninstalling.

## Session limits seen so far

- Claude can push to `main` and push new branches, but cannot delete a branch on GitHub, call the Pages settings API or create releases. The leftover branch `signature-3.4` is already in `main` and can be deleted by Abhimanyu any time.
- Claude can push to `main`, but cannot call the Pages settings API or create releases. Changing those settings is a job for Abhimanyu in the GitHub website.
- GitHub Pages is on: branch `main`, folder `/docs` (set by Abhimanyu on 13 Oct 2026).
- Two checks each failed once on the first full run after a pause and passed on every rerun (about 20 runs): test_tablet "finished list + Peaky detail" and test_info "own series: count fixing offered". Cause not found; both now print a DEBUG line with the page state if they fail. If one fails, rerun before digging, and read the DEBUG line.
- The session shell got 403 for github.io and TVmaze; the web-fetch tool could read both. Tests fake TVmaze (`tests/common.py`, `FakeTVmaze`) with plain stand-in posters.

## Agreed next update (asked for on 13 Oct 2026, not started)

(On 15 Oct he asked for series info from the internet first; that became 3.3. Name and logo are still next.)

Abhimanyu wants the next update to be exactly this, nothing else first:

1. An English app name, replacing "वॉच-लिस्ट". This is the launcher label in `android/res/values/strings.xml` plus the in-app title and subtitle.
2. A new logo (`android/res/mipmap-*/ic_launcher.png`).
3. ~~New interface colours~~: done in 3.1 as a live update (navy `#0D1628` + brass `#D4A64A`). He let Claude choose the colours.

Name and logo live in the APK, so they need a new shell build: versionCode 6; a `SHELL` bump is not required. In the same build, change the starter page background in `android/assets/index.html` and `setBackgroundColor` in `MainActivity.smali` from `#121419` (`-0xedebe7`) to `#0D1628` (`-0xf2e9d8`), so the start-up flash matches. Make the new icon fit the navy-and-brass colours.

Before building, show him two or three options for each (a picture of the icon and of one screen) and let him pick.

## History

- 1.0 / 1.1: simple list. 2.0: five-screen design (अभी, सूची, देख लीं, विवरण, सेटिंग). 2.1: tablet layout.
- 3.0 (shell 3, versionCode 5): live updates, "क्या नया है", backup reminder dot.
- 3.1 (live, build 31): navy-and-brass colours.
- 3.2 (live, build 32): real posters, blurred poster backdrop on the detail screen, poster picker, brass seal when a series is finished, seal art for empty screens.
- 3.3 (live, build 33): suggestions from TVmaze while typing a name on the add screen (fills channel, exact counts, poster); "जानकारी" on the detail screen (years, status, channel, language, runtime, rating, genres in Hindi, next episode date); exact-count fix for his own series. Checks in `tests/test_info.py`.
- 3.4 (live, build 34): his signature (approved 15 Oct 2026): opening screen, owner card in settings with the on/off switch, signature and © line on the GitHub front page.
- Talked about, not asked to build yet: linking with a calendar ("कैलेंडर में जोड़ें" button for the next episode is the easy first step).
- Agreed later steps for graphics: chess-piece emblems for the five character types, then a weekly-episodes chart. That chart needs a watch log with dates, and must have no streaks.

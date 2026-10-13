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
6. Commit and push to `main`. Pages redeploys in about a minute. Confirm with `curl -s https://abhimanyugaur58-stack.github.io/Watchlist/version.json`.
7. Tell him in Hindi what changed. The phone and tablet pick it up the next time the app opens; "सेटिंग → अभी अपडेट जाँचें" forces a check.

## When a new APK is needed (rare)

Only for shell changes: permissions, icon, app name, or native code in `smali/`. Also when the bundled copy should catch up.

1. Change `android/`.
2. If the starter page or native behaviour changed, bump `var SHELL` in `android/assets/index.html`.
3. Set `var BUNDLED` to the current `BUILD`.
4. Bump `versionCode` (+1) and `versionName` in `android/apktool.yml`.
5. Run `tools/build.sh`. It copies `docs/app.html` into the APK, builds with Apktool 2.10.0, and signs with `android/signing/debug.keystore` (alias `androiddebugkey`, password `android`). It refuses to finish if the certificate SHA-256 is not `1e08a903aef9c3a721510b64ec764d01d3d094eb954161b62544ea8f187b5953`.
   - Android only installs an update over the old app when the key matches. A different key means he has to uninstall, and that wipes his data.
6. Publish `dist/watchlist.apk` as a GitHub release asset named `watchlist.apk` (tag `vX.Y`). The app's "नया ऐप डाउनलोड करें" button opens `releases/latest`.
7. If live pages now need the new shell, set `minShell` in `docs/version.json`, so older phones are told to install the APK instead of downloading a page they can't run.
8. Remind him to copy a backup code before installing, and to install over the old app without uninstalling.

## History

- 1.0 / 1.1: simple list. 2.0: five-screen design (अभी, सूची, देख लीं, विवरण, सेटिंग). 2.1: tablet layout.
- 3.0 (shell 3, versionCode 5): live updates, "क्या नया है", backup reminder dot.

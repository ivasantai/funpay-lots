# Development and builds

**English** · [Русский](DEVELOPMENT.ru.md)

## Running from source

Windows:
```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py
```

macOS and Linux:
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```
On Linux `requirements.txt` installs pywebview with Qt (PyQt6 + PyQt6-WebEngine); you may need the system
libraries from the “System libraries for Qt” step in `.github/workflows/build.yml`.

The environment variable `FPL_DEBUG=1` starts the window in pywebview debug mode (with developer tools).

## The interface without the Python side
```bash
python -m http.server 8765 -d ui
```
Open `http://localhost:8765/index.html?mock` — the interface runs on fake data from `ui/mock.js`.
Handy for layout changes. When you add a method to `Api`, add it to `mock.js` as well. Put only made-up
nicknames, order numbers and amounts into demo data and documentation — the repository is public.

## Interface translation
Interface texts are written in Russian directly in `ui/index.html` and in Python messages. English is the
dictionary in `tools/i18n_build.py` (`EXACT` — exact phrases, `PATTERNS` — patterns with `$1`, `$2` for numbers
and names). When you add or change a text, add its translation and rebuild the dictionary:
```bash
python tools/i18n_build.py
```
To check that nothing is left in Russian: open `index.html?mock` and run in the browser console
```js
const s = document.createElement("script"); s.src = "i18n_audit.js"; document.head.append(s);
// once loaded:
await i18nAudit()
```
The audit walks through every screen in English and returns the strings that stayed in Russian
(lot titles, messages and reviews from the demo data are content and don't need translating).
How translation works — see [ARCHITECTURE.md](ARCHITECTURE.md#interface-language).

## Building

### Locally
```bash
pyinstaller --noconfirm funpay_lots.spec
```
- Windows → `dist/FunPayLots.exe` (a single file).
- macOS → `dist/FunPay Lots.app` for the architecture of the Python you build with (arm64 or x86_64).
- Linux → `dist/FunPayLots` (a single file with QtWebEngine).

Checking a build without a window: `FunPayLots --selftest` (exit code 0 — all modules, files and the dictionary
are in place). Each OS can only be built on itself — GitHub Actions handles the rest.

### GitHub Actions
`.github/workflows/build.yml` builds four versions:

| Job | Runner | Result |
|---|---|---|
| windows | `windows-latest` | `FunPayLots.exe` |
| macos arm64 | `macos-latest` | `FunPayLots-macos-arm64.zip` |
| macos x86_64 | `macos-15-intel` | `FunPayLots-macos-x86_64.zip` |
| linux | `ubuntu-22.04` (older glibc — wider compatibility) | `FunPayLots-linux-x86_64.tar.gz` |

For each: build → `--selftest` (a failure breaks the build) → a 20–25 second trial run of the window with a
screenshot (artifact `smoke-*`, doesn't affect the result — for a visual check).

- **manually:** Actions → build → Run workflow — files and screenshots in the run's artifacts;
- **on a `v*` tag:** additionally creates a GitHub Release with all four files.

## Releasing a new version
Users get updates automatically, so the version in the tag, `app.py` and `.spec` must match, and the sections in
`CHANGELOG.md` (English) and `CHANGELOG.ru.md` (Russian) must be titled `## X.Y.Z — date`: their text becomes the
release description (English, a `<!-- ru -->` marker, Russian), and the update card shows the part in the
interface language.

1. Bump the version in `app.py` (`VERSION`) and `funpay_lots.spec` (`VERSION`), update both changelogs.
2. Commit and push.
3. Create a tag:
   ```bash
   git tag v1.2.0
   ```
   ```bash
   git push origin v1.2.0
   ```
4. In about 5 minutes the release appears on the Releases page.

## Icon
Put a square image into `assets/icon-source.<png|webp|jpg>` (1024 px or more is best) and run:
```bash
python tools/make_icons.py
```
The script creates `assets/icon.ico` (Windows, rounded corners), `assets/icon.icns` (macOS, a tile with margins
following Apple's guidelines), `assets/icon.png` and `ui/icon.png`. Needs Pillow (`pip install pillow`).

## When FunPay changes its site
The client parses HTML, so FunPay layout changes can break it. What to do:
1. Look at the error text in the app (or run `python app.py` from a console — there'll be a traceback).
2. Find the request and selector used for that action in [ARCHITECTURE.md](ARCHITECTURE.md#how-the-funpay-client-works).
3. Open the same page in a browser, compare the markup (DevTools → Elements) and fix the selector in `funpay_client.py`.

The things that change most often: classes on `/lots/<node>/trade` (`tc-item`, `tc-desc-text`, `tc-price`),
`data-app-data` on the home page, the set of cookies (currently kept by `requests.Session`).

## Testing auto-update
Build the exe, put a copy into a separate folder and run it as an “old” version:
```powershell
$env:FPL_VERSION_OVERRIDE = "1.0.0"; .\FunPayLots.exe --update
```
The exe should be replaced with the latest release (compare its hash with the file from Releases) and start.
The result is in `%APPDATA%\FunPayLots\update.log`. On macOS: `FPL_VERSION_OVERRIDE=1.0.0 "FunPay Lots.app/Contents/MacOS/FunPay Lots" --update`.

## Testing the AI without a key
Requests can be pointed at a local stub that answers in the Messages API format:
`FPL_ANTHROPIC_BASE_URL=http://127.0.0.1:<port>`. This checks how the request is built (model, beta header,
JSON schema) and how the response is parsed, including `stop_reason: "refusal"`. Text quality can only be checked
with a real key.

## Manual check before a release
Use an inactive test lot so buyers don't see it:
1. Sign in with the key, load the list.
2. “New lot” → category → fill in, uncheck “Active” → create. The lot appears greyed out.
3. Change the price/title → save → open again, check the values.
4. Save with an empty price — there should be a clear error.
5. Delete the lot — it disappears from the list.
6. “Finances”: balances match the site, history loads, filters work.
7. Editor: “Fill in with AI” and “Translate” fill in the fields (needs a key in ⚙); nothing is saved by itself.
   Duplicate (the copy icon) opens a copy; bulk text/price replacement — on a disabled test lot.
8. Raise: “Raise” in the auto-raise window answers “raised” or “wait N hours”.
9. Orders, chats and analytics open; check sending messages, refunds and review replies only deliberately — these
   are actions on a real account.
10. Withdrawal window: “You receive” is calculated; “Next” shows the summary. Confirm a withdrawal only
   deliberately and for a small amount: it's a real request.
11. Switch the language to English (⚙ or RU / EN on the sign-in screen) and go through the tabs.

# Architecture

**English** · [Русский](ARCHITECTURE.ru.md)

## Stack
- **Python 3.12+** — logic and FunPay access (`requests` + `BeautifulSoup`).
- **pywebview** — a native window with a web interface: Edge WebView2 on Windows, WebKit on macOS, Qt WebEngine on Linux.
- **Plain HTML/CSS/JS, no frameworks** — the whole interface is one file, `ui/index.html`.
- **PyInstaller** — packaging into `.exe` / `.app`; **GitHub Actions** — builds for every OS.

## Files

```
app.py               window, JS ↔ Python bridge (the Api class), settings storage
funpay_client.py     FunPay client: sign-in, lots, finances and withdrawals
updater.py           checking for and installing updates from GitHub Releases
ai.py                AI (Claude API): description generation and translation into English
free_translate.py    free RU→EN translation via MyMemory (no key)
features.py          sales statistics, competitor prices, rentals, lot backup/restore
background.py        background thread (auto-raise, new orders/messages, rentals), OS notifications, tray
i18n.py              translation of Python-side messages into English (same dictionary as the interface)
ui/index.html        interface (sign-in, lists, editor, category picker, …)
ui/i18n_en.json      ru→en dictionary (built by tools/i18n_build.py)
ui/i18n_audit.js     translation check in a browser (?mock, then i18nAudit()) — not part of the app
ui/mock.js           fake API for viewing the interface in a browser (?mock)
ui/icon.png          logo in the interface
assets/              icon source and the generated icon.ico / icon.icns / icon.png
tools/make_icons.py  icon generation from assets/icon-source.*
tools/i18n_build.py  interface translation dictionary (source of ui/i18n_en.json)
funpay_lots.spec     PyInstaller configuration for Windows, macOS and Linux
.github/workflows/build.yml   builds and releases in GitHub Actions
```

## Data flow

```
ui/index.html ──window.pywebview.api.<method>()──▶ Api (app.py) ──▶ FunPayClient ──HTTPS──▶ funpay.com
       ◀──────────── {ok: true, data} | {ok: false, error} ◀────────────┘
```

Every `Api` method is wrapped in `api_call`: exceptions never reach JS; they become
`{ok: false, error: "<text for the user>"}`. FunPay errors (`FunPayError`) are shown as they are (translated
into the interface language), everything else as “Internal error” (the traceback is printed to the console).

pywebview calls `Api` methods in separate threads, so long requests don't freeze the window.

### Api methods

| Method | What it does |
|---|---|
| `state()` | whether a key is saved, version, settings, whether there's a tray |
| `set_ui_lang(lang)` | interface language for Python-side messages (`ru` / `en`) |
| `set_setting(key, value)` | language, theme, background mode, notifications, rental options |
| `accounts()` / `switch_account(id)` | list of accounts / switching |
| `events()` | background events for the window (notifications, updates) |
| `bulk_edit(node, offer, replace, price)` | text replacement and/or price change for one lot |
| `autoraise_state()` / `autoraise_set(enabled, nodes)` / `raise_now(node)` | auto-raise |
| `templates()` / `template_save(name, fields)` / `template_delete(id)` | description templates |
| `backup_lot(...)` / `backup_save(lots)` / `backup_open()` / `backup_restore(item, inactive)` | backup and restore |
| `orders(cont, state)` / `order(id)` / `refund(id)` / `review_reply(id, text)` / `rentals()` / `rental_adjust(id, minutes)` | orders and rentals |
| `chats()` / `chat_history(id)` / `send_message(id, text)` | chats |
| `stats(days)` / `competitors(node)` | analytics |
| `ai_chat_reply(chat_id, hint)` / `ai_review_reply(order_id, hint)` | AI reply drafts |
| `login(key, remember)` | sign in; without `key` — with the saved key |
| `logout()` | forget the current account's key |
| `lots()` | all categories and lots (see below) |
| `games()` | the FunPay game/category catalog for picking when creating a lot |
| `form(node, offer)` | lot form: an existing one (`offer`) or a new one (`offer=None`) |
| `save(node, fields, category_name)` | submit the form; remembers the category |
| `delete(node, offer)` / `set_active(node, offer, active)` | delete / enable-disable |
| `forget_category(node)` | remove a category from the remembered ones |
| `finance()` | balances, withdrawal methods, saved details, SBP banks, history filters |
| `transactions(filter, cont)` | a page of the transaction history; `cont` — cursor of the next page |
| `withdraw_calc(...)` | amount you receive after fees |
| `withdraw_preview(...)` / `withdraw_confirm(..., twofactor)` | the two withdrawal steps (see below) |
| `check_update()` / `install_update()` / `update_progress()` / `skip_update(v)` | auto-update |
| `ai_status()` / `ai_set_key(key)` | whether there's an AI key / check and save the key (empty — delete) |
| `ai_generate(brief, category, attributes, current, with_payment_msg, with_english)` | generate lot fields |
| `ai_translate(fields)` | translate `summary`/`desc`/`payment_msg` into English; `engine` in the response: `claude` or `free` |
| `set_translator(mode, email)` | translation mode `auto`/`free`/`claude` and an email for the MyMemory limit |
| `open_url(url)` | open in the browser (only `https://funpay.com/…`, this repository and the Anthropic console) |

pywebview also exposes public attributes of the `Api` object to JS, so internal state is kept in fields with an
underscore (`_fp`, `_store`, `_window`).

## How the FunPay client works

There's no official API — the client repeats the requests the website makes.

| Action | Request |
|---|---|
| Authorization | the `golden_key` cookie in a `requests.Session`. The session keeps the cookies the site hands out (`PHPSESSID`, `golden_seal`, etc.) |
| Who am I | `GET /` → JSON in `<body data-app-data>`: `userId`, `csrf-token`; nickname — `.user-link-name`, balance — `.badge-balance` |
| Category catalog | `GET /` → `.promo-game-item` → links `/lots/<node>/` |
| Categories with lots | `GET /users/<id>/` → `.offer-list-title` (only categories with **active** lots) |
| Own lots of a category | `GET /lots/<node>/trade` → `a.tc-item` (`data-offer`, `.tc-desc-text`, `.tc-amount`, `.tc-price`). Inactive lots have the `warning` class |
| Lot form | `GET /lots/offerEdit?node=<node>[&offer=<id>]` → `form[action*=offerSave]` |
| Save / create | `POST /lots/offerSave` (`x-requested-with: XMLHttpRequest`) with all form fields. A new lot has `offer_id=0` |
| Delete | the same save with `deleted=1` |
| Enable/disable | the same save with `active=on` or without the `active` field |

The `offerSave` response is JSON: `{"done": true, "error": false, "errors": [], "url": …}` or
`{"error": "…", "errors": [["price", "Укажите цену."], …]}`. The client replaces field names with their labels
from the form: “Цена за 1 шт.: Укажите цену” (then translated: “Price per unit: Specify the price”).

### Raising, orders, chats, storefront

| Action | Request |
|---|---|
| Game ID of a category | `GET /lots/<node>/trade` → button `.js-lot-raise[data-game][data-node]` |
| Raise | `POST /lots/raise` (`game_id`, `node_id`, `node_ids[]` — all your categories of that game). Response `{"error": false, "msg": …}` or `{"error": true, "msg": "Подождите 2 часа."}` (the wait is parsed by `parse_wait`; “час” without a number = 1 hour). If a `modal` with a category choice comes back — retry with all `node_ids[]` from it |
| Sales | `GET /orders/trade[?state=paid|closed|refunded]`, next page — `POST` with `continue`. `a.tc-item`: class `info` — pending, `warning` — refund, otherwise closed; `.tc-order`, `.tc-date-time`, `.order-desc`, `.media-user-name`, `.tc-price` |
| Order | `GET /orders/<id>/` → `.param-item` (h5 + value), `.order-review` (rating `rating<N>`, text, `.review-compiled-reply`), `.chat[data-id]` — chat ID, `button.btn-refund` — refund possible |
| Refund | `POST /orders/refund` (`id`, `csrf_token`) |
| Review reply | `POST /orders/review` (`authorId` = own ID, `text`, `rating`, `orderId`, `csrf_token`) |
| Chat list | `POST /runner/` with a `chat_bookmarks` object → `a.contact-item` (`data-id`, `data-node-msg`, class `unread`) |
| Chat history | `GET /chat/history?node=<id>&last_message=…` → `chat.messages[]` (`id`, `author`, `html`; author 0 — FunPay) |
| Send a message | `POST /runner/` with `request: {action: "chat_message", data: {node, last_message: -1, content}}` |
| Category storefront | `GET /lots/<node>/` → all `a.tc-item`: `id` from the link, `data-user`, `data-online`, `data-f-*` (parameters), `.tc-price[data-s]` — the buyer's price. Your own lots come **without** `data-user` — they're matched by ID |

Dates like “сегодня, 11:52” / “вчера, …” / “2 ноября, …” / “12 октября 2025, …” are converted to unix time by
`parse_date`; the duration from a title (“НА 3 ЧАСА”, “30 минут”, “1 месяц”) — by `parse_duration` (in minutes).
The client always works with the Russian version of the site: these parsers rely on Russian text.

### Analytics and rentals (`features.py`)
- **Statistics** — from sales (`/orders/trade`, up to 15 pages until the period is covered). Refunds are counted
  separately and aren't part of revenue. The main currency is the one with the highest revenue. Lots are grouped
  by title without the “, С подпиской, Pro” tail FunPay appends to the title in an order.
- **Competitors** — for each of your lots: the group “same `data-f-*` and same duration”, price rank
  (1 + number of cheaper offers), minimum, median, the 5 cheapest. For disabled lots (not on the storefront) —
  the market for the same duration.
- **Rentals** — orders (except refunds) with a duration of up to a week in the title; end = order time + duration +
  bonus minutes from the settings + a manual per-order adjustment (`accounts[uid].rentals_extra[number]`, minutes,
  changed by `rental_adjust(order_id, minutes)`; on change the order is removed from `rentals_done` /
  `rentals_warned` so the reminders fire again).
- **Backup** — all non-system form fields of every lot (`get_form`). Restore takes a fresh form of the category,
  fills in the fields by name and saves it as a **new** lot (disabled by default).

### Background (`background.py`)
`Worker` is a thread that wakes up every 10 seconds (or immediately via `wake`):
- **auto-raise** — for every account with auto-raise on; each game has its own next attempt time
  (`autoraise.next[game]` = FunPay's answer + 90 seconds), the last attempt is in `autoraise.last`;
- **updates** — every 30 minutes `Api.find_update()` (if `auto_update_check` is on); for each new version (except a
  skipped one) — one `update` event to the window and an OS notification. The window does the first check at
  startup; “Check for updates” in the tray menu sends the window a `check_update` event;
- **orders** (every minute) and **chats** (every 30 seconds) — only for the open account; the first pass only
  remembers what's there, after that new paid orders and unread messages produce a notification;
- **rentals** — a reminder 10 minutes before the end and when it ends, optionally an automatic message to the
  order's chat (IDs of processed orders are stored so it doesn't repeat).

Notifications: an event to the window (the interface collects them via `events()` every 5 seconds) + an OS
notification: Windows — through the tray icon (pystray), macOS — `osascript display notification`, Linux —
`notify-send`. Closing the window in background mode: the `closing` handler returns `False`, and the window hides
(Windows, tray) or is minimized (macOS/Linux).

### Finances and withdrawals

| Action | Request |
|---|---|
| Balances and withdrawal options | `GET /account/balance` → the `withdraw/withdraw` form: `select[name=currency_id]` (balances in `data-content`), JSON in `.withdraw-box[data-data]`: `currencies[cur].channels` (methods and `feeInfo`) and `extCurrencies[ext]` (`walletName`, saved `wallets`), SBP banks — `select[name=wallet_extra]` |
| History | `POST /users/transactions` with `user_id`, `filter` (`""`, `payment`, `withdraw`, `order`, `other`), `continue` (cursor). The response is HTML with `.tc-item` and a new `continue` |
| Amount you receive | `POST /withdraw/calc` (`currency_id`, `ext_currency_id`, `wallet`, `amount_int`) → `{"amount_ext": …}` |
| Withdrawal, step 1 | `POST /withdraw/withdraw` with `preview=1` → validation and summary (`wallet`, `amount_int`, `amount_ext`, `twofactor_enabled`), **no debit** |
| Withdrawal, step 2 | the same request with `preview=""` and `twofactor_code` → a withdrawal request. Errors: `error`+`msg` or `twofactor_error`+`twofactor_msg` |

The two-step scheme follows the site's logic (`app.bundle.js`, the `.withdraw-box` form handler).
For SBP (`ext_currency_id=fps`) `wallet_extra` — the bank ID — is sent as well.

### Auto-update (`updater.py`)
1. `GET https://api.github.com/repos/ivasantai/funpay-lots/releases/latest` (no token — the repository is public).
2. The version from `tag_name` is compared with `VERSION`; the release description is shown as the list of changes.
   The file is picked by OS and architecture (`updater.asset_name()`): `FunPayLots.exe`,
   `FunPayLots-macos-{arm64|x86_64}.zip`, `FunPayLots-linux-x86_64.tar.gz`.
3. Installation — only in the built app (`sys.frozen`):
   - **Windows:** the new exe is downloaded next to the old one (hidden `.FunPayLots.new.exe`); the running exe is
     moved to `%TEMP%\FunPayLots-old-<time>.exe` (Windows allows moving it, but not deleting; if TEMP is on another
     drive — to a hidden `.FunPayLots.old` next to it), the new one takes its place and starts with
     `PYINSTALLER_RESET_ENVIRONMENT=1`. The new process is created with `CREATE_BREAKAWAY_FROM_JOB`: the PyInstaller
     bootloader keeps the app in a job object that would kill the new version when the old one exits. If the job
     doesn't allow breakaway — it's started via `explorer.exe`, like a double click.
   - **macOS:** the zip is unpacked with `ditto` (keeps permissions and symlinks). Where to install: in place of the
     running `.app`; if it runs from App Translocation (a read-only copy for quarantined files) — into the real
     folder returned by `SecTranslocateCreateOriginalPathForURL` (Security.framework, via ctypes), and if that can't
     be determined or isn't writable — into `/Applications` or `~/Applications`. The old `.app` goes to a temporary
     folder, the new one is copied in place, and its quarantine flag is removed (otherwise macOS would run it from a
     read-only copy again). A background `sh` waits for the process to exit, deletes the temporary folder and runs `open`.
   - **Linux:** `FunPayLots` is extracted from the tar.gz into a temporary file next to it and atomically replaces the
     old one (`os.replace`; the running process keeps using the old file), then the new version starts in a separate
     session.
4. The current window closes. At startup `cleanup_old()` removes leftovers of the previous update; if the old
   process still holds the file, it retries in the background for up to a minute.

`FunPayLots.exe --update` — the same without the interface (result in `update.log` next to `config.json`).
`FPL_VERSION_OVERRIDE=1.0.0` makes the app think it's an old version — for testing updates.

### Window and platforms
- The interface is passed to the window as a string (`create_window(html=...)`), and the icon is embedded as a
  data URI. pywebview's built-in HTTP server isn't used: at startup it resolves the computer name, which makes
  macOS 15 ask for local network access.
- Window engine: Edge WebView2 (Windows), WKWebView (macOS), QtWebEngine via PyQt6 (Linux — it can be packed
  inside the app, unlike GTK/WebKitGTK). In the Linux build the Chromium sandbox is disabled
  (`QTWEBENGINE_DISABLE_SANDBOX=1`): in a packed app it's often unavailable because of user namespace
  restrictions, and the window only shows the app's local interface.
- The `icon` parameter of `webview.start` is passed only on Linux: on Windows it expects `.ico` and crashes on `.png`.
- `--selftest` — a build check without a window: imports every module (including this OS's window engine and the
  Anthropic SDK), checks the interface files and the translation dictionary, writes `selftest.log`, exit code 0/1.
- Startup errors go to `app.log` in the settings folder (the built app has no console).

### Interface language
The interface is written in Russian; English is the `ui/i18n_en.json` dictionary. `tools/i18n_build.py` builds it
from two parts: `EXACT` — exact phrases, `PATTERNS` — regular expressions for phrases with numbers and names
(“Выбрано: 3”, “вчера, 16:27”, “Подождите 2 часа.”). The lookup order is the same in JS (`tr()` in
`ui/index.html`) and Python (`i18n.tr()`): exact match (ignoring extra whitespace) → the first matching pattern
(groups `$1…` are translated recursively) → splitting by “ • ”, “ · ”, “ — ”, “: ” and translating the parts.
If nothing matches, the string stays as it is.

- **Window:** a `MutationObserver` translates text nodes and `placeholder`/`title` attributes on every page change,
  so the interface code doesn't need to be rewritten around `t()`. The original is kept (`WeakMap`) — switching
  back to Russian restores the text. Inputs and user content aren't translated (the `NOTR` selector: chat messages,
  lot titles in the table, values in the order card, reviews). Numbers and dates are formatted with `LOC()`
  (`ru-RU` / `en-US`).
- **Python:** `api_call` translates error texts, `Api.notify` and `Notifier.os_notify` translate notifications,
  and the tray menu takes its labels through `Notifier.translate`. The window reports the language via `set_ui_lang()`.
- **The `lang` setting:** `auto` (by `navigator.language`: ru/uk/be/kk → Russian, otherwise English), `ru`, `en`.
- The dictionary is embedded into the page at startup (`page_html()` replaces `/*I18N_EN*/`); in a browser
  (`?mock`) the page loads `i18n_en.json` itself.
- **Release notes** contain the English part, a `<!-- ru -->` marker and the Russian part (built by
  `.github/workflows/build.yml` from `CHANGELOG.md` and `CHANGELOG.ru.md`); the update card shows the part in the
  interface language.

### AI (`ai.py`)
The official `anthropic` SDK, model `claude-opus-5-5`, one `beta.messages.create` request per action:

- **Structured output** — `output_config.format` with a JSON schema (`summary`, `desc`, `payment_msg`, and `*_en`
  for translation / “English version too”), so the answer always maps onto the form fields without text parsing.
- **Effort** — `medium` for generation, `low` for translation (a simple task, faster and cheaper).
- **Refusals** — server-side fallback `fallbacks: "default"` is on (beta `server-side-fallback-2026-07-01`): if a
  safety classifier declines the request, the API retries it on the recommended model. If that one declines too,
  `stop_reason: "refusal"` is shown as a clear error.
- **The system prompt** sets the role of a FunPay copywriter and the marketplace rules (no contacts or links
  outside FunPay, no invented facts). The request includes the category, the lot's drop-down values, the brief
  and the current Russian text.
- Key check — `models.retrieve` (free, no generation).
- `import ai` is lazy: the SDK loads only on first use so startup stays fast.
- `FPL_ANTHROPIC_BASE_URL` — override the API address (for testing against a local stub).

### Free translation (`free_translate.py`)
`GET https://api.mymemory.translated.net/get?q=…&langpair=ru|en[&de=email]` — a public API without a key.
- The request limit is 500 bytes, so text is translated **line by line** (which also keeps line breaks); long
  lines are split by sentences/words into chunks of up to 450 bytes. Up to 4 requests in parallel.
- The edges of a line (`•` markers, emoji, punctuation — everything that isn't a letter/digit) are cut off before
  translation and put back afterwards: the translator loses or moves them.
- Lines without Cyrillic and duplicate lines aren't sent (saves the daily limit).
- Limit exhausted: `quotaFinished`, status 429 or the text `MYMEMORY WARNING` → a clear error.
- The engine is chosen in `Api.ai_translate`: the `translator` setting (`auto` by default: Claude if there's a key).

### Dynamic form
`get_form` turns the HTML form into a list of fields:

```json
{"name": "fields[type]", "label": "Тип подписки", "kind": "select",
 "options": [{"value": "Plus", "text": "Plus"}], "value": "Plus",
 "locale": "", "conditional": false}
```

`kind`: `text`, `textarea`, `select`, `checkbox`, `hidden` (e.g. `fields[images]`) and `system`
(`csrf_token`, `form_created_at`, `offer_id`, `node_id`, `location`, `deleted` — not shown, but sent back).
`locale: "en"` goes into the “English version” block. `conditional: true` — a field the site hides until other
fields are chosen.

The interface draws the form from this list and returns it with new `value`s — so any fields of any category are
supported without code changes. Checkboxes are sent like a browser does: `on` when checked, otherwise the field
isn't sent.

### Why the lot list is assembled from several sources
The profile shows only categories with active lots, while `/lots/<node>/trade` shows all your lots of a category,
but you need to know `node` for it. So `Api.lots()` combines:
1. categories from the profile;
2. categories saved in `config.json` (where the app has already seen or created lots);

and loads `/trade` for each of them in parallel (4 threads).

## Settings storage
`config.json` in the user's folder (paths — in the [user guide](USER_GUIDE.md#access-key-golden_key)):

```json
{
  "active": "1234567",
  "accounts": {
    "1234567": {
      "golden_key": "…", "username": "MyShop",
      "nodes": {"1355": "Аккаунты ChatGPT", "1392": "Прочее Telegram"},
      "autoraise": {"enabled": true, "nodes": [], "next": {"334": 1794050000}, "last": {"334": {"ok": false, "msg": "Подождите 3 часа."}}},
      "rentals_done": ["ORDER001"], "rentals_warned": [], "rentals_extra": {"ORDER002": 60}
    }
  },
  "templates": [{"id": "…", "name": "ChatGPT rental", "fields": {"fields[desc][ru]": "…"}}],
  "lang": "auto", "theme": "auto", "close_to_background": false, "notify_orders": true, "rental_msg": "…",
  "anthropic_key": "…", "translator": "auto"
}
```
Before 1.6.0 `golden_key` and `nodes` lived at the root — they are moved into the account at the first sign-in
with a newer version. The interface changes simple settings via `set_setting` (only keys from `SETTINGS_KEYS` in
`app.py`). The file is written atomically (via `.tmp`), with `600` permissions on macOS/Linux. The key is stored
in plain text, just like the browser stores it.

## Security
- The key is sent only to `funpay.com`. Besides FunPay the app talks to GitHub (`api.github.com` and release
  downloads) — without the key or personal data — and, only through the AI buttons, to `api.anthropic.com`
  (lot texts and the brief; the golden_key isn't sent there), and through translation without a key — to
  `api.mymemory.translated.net` (only the lot's Russian lines and, if set, the email).
- Withdrawals always take two steps: a preview from FunPay → explicit confirmation by the user.
- `open_url` opens only `https://funpay.com/…`, this repository's pages and the Anthropic console.
- All data from FunPay is escaped before it's shown in the interface (`esc()`); HTML from lots is never executed.

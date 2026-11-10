# Changelog

**English** · [Русский](CHANGELOG.ru.md)

## 1.7.0 — 2026-11-10
- 🌐 English interface: an RU / EN switch on the sign-in screen and in ⚙ → General (defaults to the system language). Error messages, notifications, the tray menu, FunPay dates and statuses are translated too. Content (lot titles, buyer messages, reviews) stays as it is.
- The release notes in the “Version … is available” card are shown in the interface language.
- The README and all documentation are now in English; Russian versions sit next to them (`*.ru.md`).

## 1.6.2 — 2026-11-09
- Check for updates without restarting: the “⟳ version” button in the header, an “Updates” section in ⚙ (“Check now”, time of the last check) and “Check for updates” in the tray icon menu.
- Automatic check every 30 minutes while the app is running (including in the background): you get a notification and an “Update” card. Can be turned off in ⚙.
- A manual check also shows a version you skipped earlier.

## 1.6.1 — 2026-11-09
- Rentals: add time from the card — “+30 min”, “+1 h” or a custom value (you can also subtract or reset). The duration is still calculated from the lot title; added time goes on top, and reminders follow the new end time.
- Rental timers update without re-rendering the cards, so their buttons no longer “swallow” clicks.

## 1.6.0 — 2026-11-07
- ⚡ Auto-raise: raises lots as soon as FunPay allows and waits the required time by itself; status and “Raise now”.
- ⧉ Lot duplication and bulk edits: change prices (exact, by %, by an amount) and replace text in all selected lots.
- 💾 Backup of all lots to a file and restore (including to another account); 📋 description templates.
- “Orders” tab: sales with filters and search, order card, review reply, refund, jump to chat; rental timers with reminders and an automatic message to the buyer.
- “Chats” tab: talk to buyers right in the app.
- ✨ AI reply drafts — for chats and reviews.
- “Analytics” tab: revenue, sales, average order, refunds, chart by day, top lots; competitor prices and your price rank.
- Multiple FunPay accounts with one-click switching.
- Background mode (tray on Windows), system notifications about orders and messages.
- Light/dark theme and hotkeys (Ctrl/⌘+1…5, N, F, R).

## 1.5.0 — 2026-11-06
- 🌐 English translation now works without an AI key — via the free MyMemory translator. List markers, emoji and line breaks are kept.
- ⚙ Settings → “Translation to English”: automatic (AI if there's a key, otherwise free), always free or always AI. You can add an email to raise the free limit from about 5,000 to 50,000 characters per day.

## 1.4.0 — 2026-11-06
- New builds: macOS on Intel (`FunPayLots-macos-x86_64.zip`) and Linux x86_64 (`FunPayLots-linux-x86_64.tar.gz`). Auto-update works there too.
- macOS: updating no longer fails with “Read-only file system” when the app isn't run from Applications (App Translocation) — the new version goes to the real app folder or to Applications, and the quarantine flag is removed.
- macOS: no more “Allow to find devices on local networks” prompt — the interface loads without an internal web server.
- Updating no longer leaves `.old` files next to the app.
- Prices in the lot list are shown as on the site (no extra decimals).
- Startup errors are written to `app.log` in the settings folder.

## 1.3.1 — 2026-11-06
- Fixed: on Windows the new version sometimes closed together with the old one right after auto-update. It now starts separately and stays open.

## 1.3.0 — 2026-11-06
- ✨ “Fill in with AI” in the lot editor: Claude writes the short and detailed descriptions (and optionally the message after payment) from a couple of sentences, taking into account the category, the lot's parameters and your style.
- 🌐 “Translate to English”: automatic translation of the lot's Russian fields into the English version, keeping emoji and formatting.
- ⚙ Settings: Anthropic API key for the AI (stored only on your computer).

## 1.2.0 — 2026-11-06
- “Finances” tab: balances per currency, transaction history with filters and paging, links to orders.
- Withdrawals: all FunPay methods (card, SBP, USDT and more), calculation of the amount you receive after fees, saved details, preview and confirmation with a 2FA code.
- Auto-update: the app checks GitHub Releases, shows a new version and installs it in one click (Windows and macOS).
- The version button in the header checks for updates manually.

## 1.1.0 — 2026-11-06
- App icon for Windows (`.ico`) and macOS (`.icns`), logo in the interface.
- Documentation: user guide, architecture, development and builds.

## 1.0.0 — 2026-11-06
- First version: sign-in with `golden_key`, lots by category (including inactive), search and filters.
- Create, edit, delete, enable/disable lots; bulk actions.
- The editor is built from the FunPay form, so fields of any category are supported.
- Builds for Windows 11 x64 and macOS arm64 via GitHub Actions.

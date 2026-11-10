# User guide

**English** · [Русский](USER_GUIDE.ru.md)

## Installation

### Windows 11 (x64)
1. Download `FunPayLots.exe` from the [Releases](https://github.com/ivasantai/funpay-lots/releases) page.
2. Run it. No installation needed — it's a single file.
3. If SmartScreen says “Windows protected your PC” (the app isn't signed with a certificate):
   “More info” → “Run anyway”.

The interface runs on Microsoft Edge WebView2, which is already part of Windows 11.

### macOS 11 Big Sur and later
| Mac | File |
|---|---|
| Apple Silicon (M1/M2/M3/M4) | `FunPayLots-macos-arm64.zip` |
| Intel | `FunPayLots-macos-x86_64.zip` |

Which Mac you have:  → “About This Mac” → “Chip” (Apple M…) or “Processor” (Intel).

1. Download your zip and unpack it.
2. **Drag “FunPay Lots.app” into Applications.** This matters: if you run it straight from Downloads,
   macOS runs the app from a temporary protected copy (App Translocation), where updates can't be installed.
3. First launch: right-click the app → “Open” → “Open”.
   If macOS still blocks it, run in Terminal:
   ```bash
   xattr -dr com.apple.quarantine "/Applications/FunPay Lots.app"
   ```

macOS versions older than 11 (Catalina and earlier) are not supported.

### Linux (x86_64)
1. Download `FunPayLots-linux-x86_64.tar.gz` and unpack it:
   ```bash
   tar xzf FunPayLots-linux-x86_64.tar.gz
   ```
2. Run it:
   ```bash
   ./FunPayLots/FunPayLots
   ```

It's a single executable with a Qt interface — no need to install Python or Qt. Works on
Ubuntu 22.04+, Debian 12+, Fedora, Arch and other distributions with a desktop (X11, or Wayland via
XWayland). If no window appears, install the system libraries that desktops usually already have
(example for Ubuntu/Debian):
```bash
sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libnss3 libegl1
```
Startup errors are written to `~/.config/funpay-lots/app.log`. There's no ARM build (Raspberry Pi etc.) yet.

## Access key (golden_key)

FunPay has no official API, so the app signs in to your account with the **golden_key** cookie —
the same one your browser keeps after you sign in on the site.

How to get it:
1. Sign in at [funpay.com](https://funpay.com) in your browser.
2. Open the developer tools: `F12` (Windows) or `⌥⌘I` (Mac; in Safari enable the “Develop” menu first).
3. Chrome/Edge: **Application → Cookies → https://funpay.com**. Firefox/Safari: **Storage → Cookies**.
4. Copy the value of `golden_key` (32 letters and digits).

> ⚠️ The key gives full access to your account, including withdrawals. Never share it.
> If the key leaks, sign out on funpay.com and change your password, then take a new key.

The “Remember on this computer” checkbox stores the key locally so the next launch signs in automatically:
- Windows: `%APPDATA%\FunPayLots\config.json`
- macOS: `~/Library/Application Support/FunPayLots/config.json`
- Linux: `~/.config/funpay-lots/config.json`

### Multiple accounts
Click your nickname in the header: there's the list of accounts (one-click switching), **“＋ Add account”**
(opens the sign-in screen; “Cancel” takes you back to the current one) and **“Sign out of …”**, which removes
the current account's key from this computer. Auto-raise works for every account that has it enabled;
notifications about orders, messages and rentals are for the account that is currently open.

## Working with lots

### List
- On the left — categories where you have lots; on the right — the lots: title, stock, price.
- **Search** looks in the title, server and lot ID.
- Filter **All / Active / Inactive**.
- **⟳** reloads everything from FunPay. Changes made on the site appear after a refresh.

Inactive lots are greyed out. The app remembers the categories where it has seen your lots, so a category
doesn't disappear from the list even if all its lots are disabled.

### Enable / disable
The toggle in the “On” column enables or disables the lot on FunPay right away.

### Edit
Click the lot title or ✎. A panel opens with the same fields as on the site: the category's own fields
(type, server, etc.), short and detailed description, message to the buyer after payment, price, stock,
automatic delivery, “Items” for automatic delivery (one per line), “Active”.
The English versions of the texts are in the “English version” block.

Fields marked **“extra”** are shown on the site only for certain values of other fields.
If FunPay requires them, it will say so in the error after saving.

### AI: description and translation
There are two buttons above the fields in the lot editor (a key is needed, see below):

- **✨ Fill in with AI** — describe the item in a couple of sentences (“rental of ChatGPT Plus for 3 hours,
  instant delivery, +1 hour for a review”) and click “Generate”. The AI writes the short and detailed
  descriptions, optionally the message to the buyer after payment and the English version right away. It takes
  into account the category, the lot's parameters (type, server…) and the text you already have — it serves as
  an example of your style, and its facts are kept.
- **🌐 Translate to English** — translates the Russian fields (short and detailed description, message after
  payment) into the “English version” block, keeping emoji and line breaks. **Works without a key too** — via
  the free MyMemory translator (see below).

**Which translator is used** — ⚙ → “Translation to English”:
- *Automatic* (default) — AI if a key is added, otherwise the free translator;
- *Always the free translator (MyMemory)* — no key or payment, lower quality than the AI;
- *Always AI* — best quality, needs a key.

The free translator has a daily limit of about 5,000 characters (roughly 3–6 descriptions). If you add an email
in the settings, the limit grows to about 50,000. The email goes only to MyMemory along with the requests.
Lines without Russian letters (e.g. only emoji or Latin names) aren't sent and don't use the limit.

The AI only fills in the fields — nothing is saved until you click “Save”. Re-read the text before saving: the
model knows nothing about your item beyond what you told it. It's instructed not to add contacts or links
outside FunPay (the marketplace rules forbid that), but it's still worth checking.

**AI key.** ⚙ in the header → “Anthropic API key”. Create a key at
[console.anthropic.com](https://console.anthropic.com/settings/keys) → API Keys (pay-as-you-go billing on your
Anthropic account; one description usually costs a fraction of a cent to a couple of cents). “Check and save
key” checks the key with a free request. The key is stored in the same `config.json` as the golden_key.

### Create a lot
**＋ New lot** → choose a category. Your categories are shown first; start typing a game or category name to
search the whole FunPay catalog, or enter a numeric category ID (it's in the address `funpay.com/lots/<ID>/`).
Fill in the form and click “Create lot”.

Tip: to see how a lot looks, create it with “Active” unchecked — buyers won't see it.

### Delete
🗑 in the row or “Delete” in the editor. Deleting is permanent: FunPay has no recycle bin.

### Duplicate
⧉ in a lot's row opens the editor for a new copy with all fields of the original lot (texts, parameters,
price, auto-delivery items, images). Change what you need (e.g. “НА 3 ЧАСА” → “НА 6 ЧАСОВ” and the price) and
click “Create lot”. Nothing is created until you do.

### Bulk actions
Tick lots on the left (the checkbox in the header selects all visible ones) — buttons appear:
- **Enable / Disable / Delete**;
- **Price…** — set an exact price, change it by % (e.g. `10` or `-15`) or add/subtract an amount.
  This is the price you receive, as in the lot form (without the FunPay fee), rounded to 0.01;
- **Replace text…** — find and replace a phrase in all texts of the selected lots (short and detailed
  description, message after payment, Russian and English versions). Case-sensitive.

Lots are processed one by one with progress; at the end you see how many were changed, unchanged and failed.

### Description templates
In the lot editor — **📋 Templates**. “Save” stores the current texts (short/detailed description, message
after payment, RU and EN) under a name; “Apply” puts them into the open lot. Handy for keeping your own
formatting for new lots and for bulk updates.

### Backup and restore
**⋯** next to “Raise”:
- **Save a backup of all lots** — reads every lot in full (all form fields) and saves a `.json` via the usual
  “Save” dialog;
- **Restore from backup** — shows the lots from the file; pick the ones you need. They're created as **new
  lots** (existing ones aren't changed), disabled by default — check them and enable. You can also move lots to
  another account this way: save a backup on one, switch, and restore on the other.

### Auto-raise
**⚡ Raise** in the header. Turn on “Raise lots automatically” and tick the categories (all by default).
The app tries to raise the lots; FunPay answers “raised” or “wait N hours”, and the next attempt is scheduled
exactly for that time. The table shows the last and next attempt; “Raise” tries right now.
FunPay raises categories of the same game together. Next to the button you see when the next attempt is.

Auto-raise works while the app is running. To keep it going when you close the window, turn on
**⚙ → “Run in the background”** (see below).

## Orders
The **“Orders”** tab:
- the list of sales with filters **All / Pending / Closed / Refunds** and search by buyer, number and lot;
  “Show more” loads older ones;
- click an order to open its card: parameters, amount, review. You can **reply to the review** (the
  **✨ AI draft** button writes a suggestion — needs an AI key), **open the chat** with the buyer,
  **refund** (with confirmation; it can't be undone, and the buyer's review may be removed).

### Rentals
At the top of the “Orders” tab — active rentals with a countdown. The duration is taken from the lot title
(“НА 3 ЧАСА”, “НА 30 МИНУТ”, “НА 24 ЧАСА”), counted from the order time; refunds are ignored.
**Add time to a specific rental** right on its card: **+30 min**, **+1 h** or **±…** — a custom value in hours
and minutes (you can also subtract time or reset the adjustment there). The duration is still calculated from
the lot title; the added time goes on top and is shown next to the duration (“1 d +1 h”). The adjustment is
remembered for that order; after changing the duration the end-of-rental reminders fire again — even if the
rental had already ended and you extended it.

In ⚙ → “Rental”:
- a reminder 10 minutes before the end and when it ends (as a notification);
- bonus minutes added to every duration (e.g. 60 if you give an hour for a review);
- an **automatic message to the buyer** when a rental ends (off by default), with your text:
  `{buyer}` — nickname, `{order}` — order number.

## Chats
The **“Chats”** tab: the last 50 conversations on the left (unread ones are marked), the messages on the right.
Messages refresh every 10 seconds. **Ctrl/⌘+Enter** sends. **✨ AI** writes a reply draft based on the recent
messages; if the field already has text, it's used as a hint (“say I'll deliver in 10 minutes”). The draft is
never sent by itself — check it and click “Send”.

## Analytics
The **“Analytics”** tab:
- **Sales** for 7 / 30 / 90 days: revenue (without refunds), number of sales and buyers, average order, refunds,
  repeat buyers, a revenue chart by day (hover a bar for details) and top lots;
- **Competitor prices**: pick a category — for each of your lots you see your storefront price, your rank by
  price among similar offers (same category parameters and same duration from the title; 1 is the cheapest),
  the minimum and median price and “Cheapest” — the 5 cheapest competitors with links. Prices are as buyers see
  them (with the FunPay fee). Disabled lots aren't on the storefront — for them the market for the same duration
  is shown.

## Language, background, notifications, theme, hotkeys
⚙ → “General” and “Notifications”:
- **Language** — English or Russian (by default — the system language). You can also switch it on the sign-in
  screen (RU / EN in the corner). The whole interface, error messages, notifications and the tray icon menu are
  translated, and so are FunPay dates and statuses. Lot titles, buyer messages, reviews and a category's own
  fields stay as they are on FunPay;
- **Run in the background** — closing the window doesn't quit the app: on Windows it hides to the tray (icon next
  to the clock: “Open”, “Raise lots now”, “Check for updates”, “Quit”), on macOS and Linux it's minimized to the
  Dock / taskbar. Auto-raise, notifications and rentals keep working;
- **notifications** about new orders, new messages and (optionally) every auto-raise — system notifications plus
  pop-ups in the window;
- **Theme** — system, light or dark.

Hotkeys (⌘ instead of Ctrl on a Mac): **Ctrl+1…5** — tabs, **Ctrl+N** — new lot, **Ctrl+F** — search,
**Ctrl+R** — refresh the current tab, **Esc** — close a window/panel.

## Finances

The **“Finances”** tab in the header.

- **Balance** — per currency (dollars, rubles, euros), as on the FunPay “Finances” page.
- **Transaction history** — orders, withdrawals, top-ups and more. Filters at the top; “Show more” loads older
  transactions. Clicking “Order #…” opens the order on the site.

### Withdrawing funds
1. Click **“Withdraw”** under the currency you need.
2. Choose a method (card, SBP, USDT TRC20, etc.). The FunPay fee for that method is shown below the list.
   For SBP also choose a bank.
3. Enter the details. Details saved on FunPay are filled in automatically and are in the field's drop-down list.
4. Enter the amount (“All” — the whole balance). FunPay calculates “You receive” itself, with the fee and rate.
5. **“Next”** — FunPay checks the data and shows the result. At this step **no money is debited**.
6. Check the details and amounts, enter the code from your authenticator app if 2FA is on, and click
   **“Withdraw …”**. FunPay creates a request, and it appears in the transaction history.

You can cancel a request on the FunPay site while it hasn't been processed.

## Updates

The app checks for new versions at startup. If there's a new one, a card with the version number and the list of
changes appears in the bottom right:
- **Update** — download and install; the app restarts as the new version.
- **Later** — remind me at the next launch.
- **Skip** — don't remind me about this version.

You don't need to restart the app to find out about a new version:
- **automatically** — while the app is running (including in the background), it checks GitHub every 30 minutes;
  you get a notification and the “Update” card. Can be turned off in ⚙ → “Updates”;
- **manually** — the **⟳ v…** button in the header, **⚙ → “Updates” → “Check now”** (with the time of the last
  check) or **“Check for updates”** in the tray icon menu (Windows). A manual check also shows a version you
  skipped earlier.

The update replaces the current version, with no extra files left behind (the old copy goes to a temporary
folder and is deleted at the next launch).

- **Windows:** if the app is in a folder without write access (e.g. `Program Files`), move it to the desktop
  or Downloads.
- **macOS:** if the app isn't run from Applications and macOS keeps it in a protected copy, the update is
  installed where you launched it from, or, if that fails, to Applications.
- **Linux:** the `FunPayLots` file is replaced in place; you need write access to its folder.

> Versions before 1.2.0 can't update themselves — download 1.2.0 manually once.
> In versions 1.2.0–1.3.0 on Windows the app may close after “Update” without reopening —
> just start it again: the file is already updated. Since 1.3.1 the restart is automatic.
> On a Mac, versions before 1.4.0 can't update when not run from Applications (error
> “Read-only file system … AppTranslocation”): move the app to Applications and click “Update”
> again — or download the new version manually once.

## Limitations
- Lot **images** are kept as they are (including when duplicating and in backups); adding and changing them still
  has to be done on the site. Images in chats open in the browser.
- **Chats** — the last 50 conversations, as in the list on the site; sending images is only possible on the site.
- **Rentals** are calculated from the lot title; if the title has no duration, the order won't appear in rentals.
- **Currency categories** (in-game currency, `/chips/…`) aren't supported — FunPay uses a different editor for them.

## Troubleshooting

| Message | What to do |
|---|---|
| “The key didn't work” | The key is outdated or was copied incompletely. Take a fresh `golden_key`. |
| “FunPay rejected the request (403)” | Same: refresh the key. If that doesn't help, try later or from another network. |
| “Can't reach FunPay” | Check your internet connection / VPN. |
| “Fill in this field…” when saving | FunPay requires a mandatory field — its name is in the error. |
| ⚠ next to a category | The category didn't load (e.g. it was removed on FunPay). Remove it with “Remove category from the list”. |
| “The Anthropic key was rejected” | Check the key in ⚙: it starts with `sk-ant-` and must not be revoked. |
| “Your Anthropic account is out of credit” | Top up at console.anthropic.com → Billing. |
| “The free translation limit for today is used up” | Wait until tomorrow, add an email in ⚙ or add an AI key. |
| “The AI refused to write this text” | Rephrase your input more simply and specifically. |
| “Invalid 2FA code” when withdrawing | Enter a fresh code: it changes every 30 seconds. |
| “You receive” shows “—” | For some methods FunPay calculates the amount only after you enter the details. Fill them in. |
| Can't update | Move the app to a folder with write access or download the new version from Releases. |
| Empty window (Windows) | Install the [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/). |

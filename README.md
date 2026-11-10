<p align="center"><img src="assets/icon.png" width="128" alt="FunPay Lots"></p>

<h1 align="center">FunPay Lots</h1>

<p align="center">A desktop app for managing your lots on FunPay — Windows, macOS (Apple Silicon and Intel) and Linux.</p>

<p align="center"><b>English</b> · <a href="README.ru.md">Русский</a></p>

## Features
- All your lots grouped by category, including inactive ones; search and status filter.
- Create, edit and delete lots; enable/disable with a single toggle.
- Bulk actions: enable, disable, delete, change price, replace text; duplicate lots.
- Auto-raise, backup and restore, description templates.
- Orders, review replies, refunds, chats with buyers, rental timers.
- Sales analytics and competitor prices.
- Multiple accounts, background mode with notifications, light/dark theme, hotkeys.
- Interface in English and Russian.
- The lot editor mirrors the FunPay form, so the fields of any category are supported.
- AI (Claude): a lot description from a couple of sentences, and translation into English.
- Free English translation without a key (MyMemory).
- Finances: balances, transaction history, withdrawals with fee calculation and 2FA.
- Auto-update from GitHub Releases.
- Sign-in with your account key (`golden_key`); the key is stored only on your computer.

## Download
[Releases](https://github.com/ivasantai/funpay-lots/releases):

| System | File |
|---|---|
| Windows 10/11 x64 | `FunPayLots.exe` |
| macOS 11+ on Apple Silicon (M1–M4) | `FunPayLots-macos-arm64.zip` |
| macOS 11+ on Intel | `FunPayLots-macos-x86_64.zip` |
| Linux x86_64 | `FunPayLots-linux-x86_64.tar.gz` |

## Documentation
- [User guide](docs/USER_GUIDE.md): installation, where to get the key, working with lots, troubleshooting.
- [Architecture](docs/ARCHITECTURE.md): how the app is built, FunPay requests, data formats.
- [Development and builds](docs/DEVELOPMENT.md): running from source, building, releases, what to do when FunPay changes its site.
- [Changelog](CHANGELOG.md)

Documentation is also available [in Russian](README.ru.md).

## Quick start for developers
```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt   # Windows: .venv\Scripts\pip
.venv/bin/python app.py
```

> FunPay has no official API: the app uses the same requests as the website and may need fixes
> if FunPay changes its pages.

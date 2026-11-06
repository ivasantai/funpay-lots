# FunPay Lots

Десктоп-приложение для управления своими лотами на FunPay: список, поиск, включение/выключение,
создание, редактирование и удаление (в том числе массово). Windows 11 x64 и macOS (Apple Silicon).

## Ключ
У FunPay нет официального API, поэтому «API-ключ» — это cookie **golden_key** вашего аккаунта:
funpay.com → F12 → Application/Storage → Cookies → `golden_key`.
Ключ хранится только локально: `%APPDATA%\FunPayLots\config.json` (Windows) или
`~/Library/Application Support/FunPayLots/config.json` (macOS). Кнопка «Выйти» удаляет его.

## Что умеет
- Все свои лоты по разделам, включая неактивные (берутся со страниц `/lots/<раздел>/trade`).
- Редактор строится из настоящей формы FunPay, поэтому поля конкретного раздела подтягиваются сами.
- Новый лот: поиск раздела по всему каталогу FunPay или по ID.
- Картинки сохраняются как есть; менять их пока нужно на сайте. Разделы валюты (chips) не поддерживаются.

## Запуск из исходников
```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt      # macOS: .venv/bin/pip
.venv\Scripts\python app.py
```
Интерфейс без Python на демо-данных: `python -m http.server -d ui`, затем открыть `/index.html?mock`.

## Сборка
- **Windows:** `pyinstaller --noconfirm funpay_lots.spec` → `dist/FunPayLots.exe`.
- **macOS (M1/M2):** на маке та же команда → `dist/FunPay Lots.app`, или через GitHub Actions
  (`.github/workflows/build.yml`: запуск вручную или по тегу `v*`, собирает обе версии).
  Приложение не подписано: при первом запуске правый клик → «Открыть», либо
  `xattr -dr com.apple.quarantine "/Applications/FunPay Lots.app"`.

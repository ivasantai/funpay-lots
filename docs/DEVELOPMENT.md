# Разработка и сборка

## Запуск из исходников

Windows:
```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py
```

macOS:
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Переменная окружения `FPL_DEBUG=1` запускает окно в режиме отладки pywebview (с инструментами разработчика).

## Интерфейс без Python-части
```bash
python -m http.server 8765 -d ui
```
Откройте `http://localhost:8765/index.html?mock` — интерфейс работает на фейковых данных из `ui/mock.js`.
Удобно для правок вёрстки. Новый метод в `Api` добавляйте и в `mock.js`.

## Сборка

### Локально
```bash
pyinstaller --noconfirm funpay_lots.spec
```
- Windows → `dist/FunPayLots.exe` (один файл, ~14 МБ).
- macOS → `dist/FunPay Lots.app` (собирать на маке с Apple Silicon).

С Windows собрать macOS-версию нельзя — для этого есть GitHub Actions.

### GitHub Actions
`.github/workflows/build.yml` собирает обе версии:
- **вручную:** Actions → build → Run workflow — файлы появятся в артефактах запуска;
- **по тегу `v*`:** дополнительно создаётся GitHub Release с `FunPayLots.exe` и `FunPayLots-macos-arm64.zip`.

Раннеры: `windows-latest` и `macos-latest` (arm64).

## Выпуск новой версии
1. Поднимите версию в `app.py` (`VERSION`) и `funpay_lots.spec` (`VERSION`), допишите `CHANGELOG.md`.
2. Закоммитьте и запушьте.
3. Поставьте тег:
   ```bash
   git tag v1.2.0
   ```
   ```bash
   git push origin v1.2.0
   ```
4. Через ~5 минут релиз появится на странице Releases.

## Иконка
Положите квадратную картинку в `assets/icon-source.<png|webp|jpg>` (лучше от 1024 px) и выполните:
```bash
python tools/make_icons.py
```
Скрипт сделает `assets/icon.ico` (Windows, скруглённые углы), `assets/icon.icns` (macOS, плитка с полями
по гайдлайнам Apple), `assets/icon.png` и `ui/icon.png`. Нужен Pillow (`pip install pillow`).

## Когда FunPay меняет сайт
Клиент разбирает HTML, поэтому изменения вёрстки FunPay могут его сломать. Порядок действий:
1. Посмотрите текст ошибки в приложении (или запустите `python app.py` из консоли — там будет трассировка).
2. Найдите в [ARCHITECTURE.md](ARCHITECTURE.md#как-работает-клиент-funpay) запрос и селектор, который используется для этого действия.
3. Откройте ту же страницу в браузере, сверьте разметку (DevTools → Elements) и поправьте селектор в `funpay_client.py`.

Чаще всего меняются: классы в `/lots/<node>/trade` (`tc-item`, `tc-desc-text`, `tc-price`),
`data-app-data` на главной, набор cookie (сейчас их сохраняет `requests.Session`).

## Ручная проверка перед релизом
Проверяйте на неактивном тестовом лоте, чтобы его не увидели покупатели:
1. Вход по ключу, загрузка списка.
2. «Новый лот» → раздел → заполнить, снять «Активное» → создать. Лот появляется серым.
3. Изменить цену/название → сохранить → открыть снова, проверить значения.
4. Сохранить с пустой ценой — должна быть понятная ошибка.
5. Удалить лот — он пропадает из списка.

# Разработка и сборка

## Запуск из исходников

Windows:
```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py
```

macOS и Linux:
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```
На Linux `requirements.txt` ставит pywebview с Qt (PyQt6 + PyQt6-WebEngine); могут понадобиться системные
библиотеки из шага «System libraries for Qt» в `.github/workflows/build.yml`.

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
- Windows → `dist/FunPayLots.exe` (один файл).
- macOS → `dist/FunPay Lots.app` под архитектуру Python, на котором собираете (arm64 или x86_64).
- Linux → `dist/FunPayLots` (один файл с QtWebEngine).

Проверка сборки без окна: `FunPayLots --selftest` (код возврата 0 — все модули и файлы на месте).
Каждая ОС собирается только на себе — для остальных есть GitHub Actions.

### GitHub Actions
`.github/workflows/build.yml` собирает четыре версии:

| Задача | Раннер | Результат |
|---|---|---|
| windows | `windows-latest` | `FunPayLots.exe` |
| macos arm64 | `macos-latest` | `FunPayLots-macos-arm64.zip` |
| macos x86_64 | `macos-15-intel` | `FunPayLots-macos-x86_64.zip` |
| linux | `ubuntu-22.04` (старый glibc — шире совместимость) | `FunPayLots-linux-x86_64.tar.gz` |

Для каждой: сборка → `--selftest` (падение ломает сборку) → пробный запуск окна на 20–25 секунд со
скриншотом экрана (артефакт `smoke-*`, на результат не влияет — для визуальной проверки).

- **вручную:** Actions → build → Run workflow — файлы и скриншоты в артефактах запуска;
- **по тегу `v*`:** дополнительно создаётся GitHub Release со всеми четырьмя файлами.

## Выпуск новой версии
Пользователи получают обновление автоматически, поэтому номер версии в теге, `app.py` и `.spec`
должен совпадать, а раздел в `CHANGELOG.md` — называться `## X.Y.Z — дата`: его текст становится
описанием релиза и показывается в карточке обновления.

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

## Проверка автообновления
Соберите exe, положите копию в отдельную папку и запустите её как «старую» версию:
```powershell
$env:FPL_VERSION_OVERRIDE = "1.0.0"; .\FunPayLots.exe --update
```
Exe должен замениться последним релизом (сверьте хэш с файлом из Releases) и запуститься.
Результат — в `%APPDATA%\FunPayLots\update.log`. На macOS аналогично: `FPL_VERSION_OVERRIDE=1.0.0 "FunPay Lots.app/Contents/MacOS/FunPay Lots" --update`.

## Проверка нейросети без ключа
Запросы можно направить на локальную заглушку, которая отвечает в формате Messages API:
`FPL_ANTHROPIC_BASE_URL=http://127.0.0.1:<порт>`. Так проверяется сборка запроса (модель, beta-заголовок,
JSON-схема) и разбор ответа, включая `stop_reason: "refusal"`. Качество текста проверяется только с настоящим ключом.

## Ручная проверка перед релизом
Проверяйте на неактивном тестовом лоте, чтобы его не увидели покупатели:
1. Вход по ключу, загрузка списка.
2. «Новый лот» → раздел → заполнить, снять «Активное» → создать. Лот появляется серым.
3. Изменить цену/название → сохранить → открыть снова, проверить значения.
4. Сохранить с пустой ценой — должна быть понятная ошибка.
5. Удалить лот — он пропадает из списка.
6. «Финансы»: балансы совпадают с сайтом, история подгружается, фильтры работают.
7. Редактор: «✨ Заполнить с ИИ» и «🌐 Перевести» заполняют поля (нужен ключ в ⚙), сохранение не происходит само.
8. Окно вывода: «К получению» считается; шаг «Далее» показывает итог. Подтверждать вывод — только
   осознанно и на небольшую сумму: это настоящая заявка.

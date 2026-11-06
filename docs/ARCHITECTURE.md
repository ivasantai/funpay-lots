# Устройство проекта

## Стек
- **Python 3.12+** — логика и работа с FunPay (`requests` + `BeautifulSoup`).
- **pywebview** — нативное окно с веб-интерфейсом: Edge WebView2 на Windows, WebKit на macOS, Qt WebEngine на Linux.
- **HTML/CSS/JS без фреймворков** — весь интерфейс в одном файле `ui/index.html`.
- **PyInstaller** — упаковка в `.exe` / `.app`; **GitHub Actions** — сборка под обе ОС.

## Файлы

```
app.py               окно, мост JS ↔ Python (класс Api), хранение настроек
funpay_client.py     клиент FunPay: вход, лоты, финансы и вывод
updater.py           проверка и установка обновлений из GitHub Releases
ai.py                нейросеть (Claude API): генерация описания и перевод на английский
ui/index.html        интерфейс (вход, список, редактор, выбор раздела)
ui/mock.js           фейковое API для просмотра интерфейса в браузере (?mock)
ui/icon.png          логотип в интерфейсе
assets/              исходник иконки и сгенерированные icon.ico / icon.icns / icon.png
tools/make_icons.py  генерация иконок из assets/icon-source.*
funpay_lots.spec     конфигурация PyInstaller для Windows и macOS
.github/workflows/build.yml   сборка и релиз в GitHub Actions
```

## Поток данных

```
ui/index.html ──window.pywebview.api.<метод>()──▶ Api (app.py) ──▶ FunPayClient ──HTTPS──▶ funpay.com
       ◀──────────── {ok: true, data} | {ok: false, error} ◀────────────┘
```

Каждый метод `Api` обёрнут в `api_call`: исключения не уходят в JS, а превращаются в
`{ok: false, error: "<текст для пользователя>"}`. Ошибки FunPay (`FunPayError`) показываются как есть,
остальные — как «Внутренняя ошибка» (трассировка печатается в консоль).

pywebview вызывает методы `Api` в отдельных потоках, поэтому долгие запросы не замораживают окно.

### Методы Api

| Метод | Что делает |
|---|---|
| `state()` | есть ли сохранённый ключ, версия |
| `login(key, remember)` | вход; без `key` — по сохранённому ключу |
| `logout()` | забыть ключ |
| `lots()` | все разделы и лоты (см. ниже) |
| `games()` | каталог игр/разделов FunPay для выбора при создании |
| `form(node, offer)` | форма лота: существующего (`offer`) или нового (`offer=None`) |
| `save(node, fields, category_name)` | отправить форму; запоминает раздел |
| `delete(node, offer)` / `set_active(node, offer, active)` | удаление / вкл-выкл |
| `forget_category(node)` | убрать раздел из запомненных |
| `finance()` | балансы, способы вывода, сохранённые реквизиты, банки СБП, фильтры истории |
| `transactions(filter, cont)` | страница истории операций; `cont` — курсор следующей страницы |
| `withdraw_calc(...)` | сумма к получению с учётом комиссии |
| `withdraw_preview(...)` / `withdraw_confirm(..., twofactor)` | два шага вывода (см. ниже) |
| `check_update()` / `install_update()` / `update_progress()` / `skip_update(v)` | автообновление |
| `ai_status()` / `ai_set_key(key)` | есть ли ключ нейросети / проверить и сохранить ключ (пустой — удалить) |
| `ai_generate(brief, category, attributes, current, with_payment_msg, with_english)` | сгенерировать поля лота |
| `ai_translate(fields)` | перевести `summary`/`desc`/`payment_msg` на английский |
| `open_url(url)` | открыть в браузере (только `https://funpay.com/…` и страницы этого репозитория) |

Публичные атрибуты объекта `Api` pywebview тоже пробрасывает в JS, поэтому внутреннее состояние
хранится в полях с подчёркиванием (`_fp`, `_store`, `_window`).

## Как работает клиент FunPay

Официального API нет — клиент повторяет запросы, которые делает сайт.

| Действие | Запрос |
|---|---|
| Авторизация | cookie `golden_key` в `requests.Session`. Сессия сама сохраняет выданные сайтом cookie (`PHPSESSID`, `golden_seal` и т. д.) |
| Кто я | `GET /` → JSON в атрибуте `<body data-app-data>`: `userId`, `csrf-token`; ник — `.user-link-name`, баланс — `.badge-balance` |
| Каталог разделов | `GET /` → `.promo-game-item` → ссылки `/lots/<node>/` |
| Разделы с лотами | `GET /users/<id>/` → `.offer-list-title` (только разделы с **активными** лотами) |
| Свои лоты раздела | `GET /lots/<node>/trade` → `a.tc-item` (`data-offer`, `.tc-desc-text`, `.tc-amount`, `.tc-price[data-s]`). Неактивные лоты имеют класс `warning` |
| Форма лота | `GET /lots/offerEdit?node=<node>[&offer=<id>]` → `form[action*=offerSave]` |
| Сохранить / создать | `POST /lots/offerSave` (`x-requested-with: XMLHttpRequest`) со всеми полями формы. Новый лот — `offer_id=0` |
| Удалить | то же сохранение с `deleted=1` |
| Вкл/выкл | то же сохранение с `active=on` или без поля `active` |

Ответ `offerSave` — JSON: `{"done": true, "error": false, "errors": [], "url": …}` или
`{"error": "…", "errors": [["price", "Укажите цену."], …]}`. Клиент подставляет вместо имён полей
их подписи из формы: «Цена за 1 шт.: Укажите цену».

### Финансы и вывод

| Действие | Запрос |
|---|---|
| Балансы и настройки вывода | `GET /account/balance` → форма `withdraw/withdraw`: `select[name=currency_id]` (балансы в `data-content`), JSON в `.withdraw-box[data-data]`: `currencies[cur].channels` (способы и `feeInfo`) и `extCurrencies[ext]` (`walletName`, сохранённые `wallets`), банки СБП — `select[name=wallet_extra]` |
| История | `POST /users/transactions` с `user_id`, `filter` (`""`, `payment`, `withdraw`, `order`, `other`), `continue` (курсор). Ответ — HTML с `.tc-item` и новым `continue` |
| Сумма к получению | `POST /withdraw/calc` (`currency_id`, `ext_currency_id`, `wallet`, `amount_int`) → `{"amount_ext": …}` |
| Вывод, шаг 1 | `POST /withdraw/withdraw` с `preview=1` → проверка и итог (`wallet`, `amount_int`, `amount_ext`, `twofactor_enabled`), **без списания** |
| Вывод, шаг 2 | тот же запрос с `preview=""` и `twofactor_code` → заявка на вывод. Ошибки: `error`+`msg` или `twofactor_error`+`twofactor_msg` |

Двухшаговая схема повторяет логику сайта (`app.bundle.js`, обработчик формы `.withdraw-box`).
Для СБП (`ext_currency_id=fps`) дополнительно отправляется `wallet_extra` — ID банка.

### Автообновление (`updater.py`)
1. `GET https://api.github.com/repos/ivasantai/funpay-lots/releases/latest` (без токена — репозиторий публичный).
2. Версия из `tag_name` сравнивается с `VERSION`; описание релиза показывается как список изменений.
   Файл выбирается по ОС и архитектуре (`updater.asset_name()`): `FunPayLots.exe`,
   `FunPayLots-macos-{arm64|x86_64}.zip`, `FunPayLots-linux-x86_64.tar.gz`.
3. Установка — только в собранной версии (`sys.frozen`):
   - **Windows:** новый exe скачивается рядом (скрытый `.FunPayLots.new.exe`); запущенный exe
     переносится во `%TEMP%\FunPayLots-old-<время>.exe` (Windows разрешает перенос, но не удаление; если
     TEMP на другом диске — в скрытый `.FunPayLots.old` рядом), новый встаёт на его место и запускается
     с `PYINSTALLER_RESET_ENVIRONMENT=1`. Новый процесс создаётся с `CREATE_BREAKAWAY_FROM_JOB`: загрузчик
     PyInstaller держит приложение в job object, который при выходе старой версии убил бы и новую. Если job
     не разрешает выход — запуск через `explorer.exe`, как двойной клик.
   - **macOS:** zip распаковывается через `ditto` (сохраняет права и симлинки). Куда ставить: на место
     запущенного `.app`; если он запущен из App Translocation (read-only копия для файлов с карантином) —
     в настоящую папку, которую возвращает `SecTranslocateCreateOriginalPathForURL` (Security.framework,
     через ctypes), а если её не узнать или там нет прав — в `/Applications` или `~/Applications`.
     Старый `.app` уходит во временную папку, новый копируется на место, с него снимается карантин
     (иначе macOS снова запустит его из read-only копии). Фоновый `sh` ждёт выхода процесса, удаляет
     временную папку и делает `open`.
   - **Linux:** из tar.gz извлекается `FunPayLots` во временный файл рядом и атомарно заменяет старый
     (`os.replace`; запущенный процесс продолжает работать со старым файлом), затем новая версия
     запускается в отдельной сессии.
4. Текущее окно закрывается. При старте `cleanup_old()` удаляет остатки прошлого обновления; если старый
   процесс ещё держит файл, попытки повторяются в фоне до минуты.

`FunPayLots.exe --update` — то же без интерфейса (результат в `update.log` рядом с `config.json`).
`FPL_VERSION_OVERRIDE=1.0.0` заставляет приложение считать себя старой версией — для проверки обновления.

### Окно и платформы
- Интерфейс передаётся в окно строкой (`create_window(html=...)`), иконка встраивается как data URI.
  Встроенный HTTP-сервер pywebview не используется: при запуске он резолвит имя компьютера, из-за чего
  macOS 15 показывает запрос доступа к локальной сети.
- Движок окна: Edge WebView2 (Windows), WKWebView (macOS), QtWebEngine через PyQt6 (Linux — его можно
  упаковать внутрь приложения, в отличие от GTK/WebKitGTK). На Linux в собранной версии отключена
  песочница Chromium (`QTWEBENGINE_DISABLE_SANDBOX=1`): в упакованном приложении она часто недоступна
  из-за ограничений user namespaces, а окно показывает только локальный интерфейс приложения.
- Параметр `icon` у `webview.start` передаётся только на Linux: на Windows он ждёт `.ico` и падает на `.png`.
- `--selftest` — проверка сборки без окна: импортирует все модули (включая движок окна этой ОС
  и SDK Anthropic), проверяет файлы интерфейса, пишет `selftest.log`, код возврата 0/1.
- Ошибки запуска пишутся в `app.log` в папке настроек (у собранного приложения нет консоли).

### Нейросеть (`ai.py`)
Официальный SDK `anthropic`, модель `claude-opus-5-5`, один запрос `beta.messages.create` на действие:

- **Структурированный ответ** — `output_config.format` с JSON-схемой (`summary`, `desc`, `payment_msg`
  и при переводе/«сразу на английском» — `*_en`), поэтому ответ всегда разбирается в поля формы без парсинга текста.
- **Effort** — `medium` для генерации, `low` для перевода (простая задача, быстрее и дешевле).
- **Отказы** — включён серверный резерв `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`):
  если классификатор безопасности отклонит запрос, API сам повторит его на рекомендованной модели.
  Если отказала и она — `stop_reason: "refusal"` показывается как понятная ошибка.
- **Системный промпт** задаёт роль копирайтера FunPay и правила площадки (без контактов и ссылок вне FunPay,
  без выдуманных фактов). В запрос уходят раздел, значения выпадающих полей лота, вводные и текущий русский текст.
- Проверка ключа — `models.retrieve` (бесплатно, без генерации).
- `import ai` делается лениво: SDK загружается только при первом использовании, чтобы не замедлять старт.
- `FPL_ANTHROPIC_BASE_URL` — подменить адрес API (для проверки на локальной заглушке).

### Динамическая форма
`get_form` превращает HTML-форму в список полей:

```json
{"name": "fields[type]", "label": "Тип подписки", "kind": "select",
 "options": [{"value": "Plus", "text": "Plus"}], "value": "Plus",
 "locale": "", "conditional": false}
```

`kind`: `text`, `textarea`, `select`, `checkbox`, `hidden` (например `fields[images]`) и `system`
(`csrf_token`, `form_created_at`, `offer_id`, `node_id`, `location`, `deleted` — не показываются, но
отправляются обратно). `locale: "en"` уходит в блок «English version». `conditional: true` — поле,
которое сайт скрывает до выбора других полей.

Интерфейс рисует форму по этому списку и возвращает его же с новыми `value` — поэтому любые поля любых
разделов поддерживаются без доработок кода. Чекбоксы отправляются как в браузере: `on`, если отмечен,
иначе поле не отправляется.

### Почему список лотов собирается из нескольких источников
Профиль показывает только разделы с активными лотами, а страница `/lots/<node>/trade` — все свои лоты
раздела, но для неё нужно знать `node`. Поэтому `Api.lots()` объединяет:
1. разделы из профиля;
2. разделы, сохранённые в `config.json` (где приложение уже видело лоты или создавало их);

и параллельно (4 потока) загружает `/trade` для каждого.

## Хранение настроек
`config.json` в папке пользователя (пути — в [USER_GUIDE.md](USER_GUIDE.md#ключ-доступа-golden_key)):

```json
{
  "golden_key": "…",
  "nodes": {"1355": "Аккаунты ChatGPT", "1392": "Прочее Telegram"}
}
```
Файл пишется атомарно (через `.tmp`), на macOS — с правами `600`. Ключ хранится открытым текстом,
так же как его хранит браузер.

## Безопасность
- Ключ уходит только на `funpay.com`. Кроме FunPay приложение обращается к GitHub
  (`api.github.com` и скачивание релиза) — без ключа и личных данных — и, только по кнопкам ИИ,
  к `api.anthropic.com` (тексты лота и вводные; golden_key туда не отправляется).
- Вывод средств всегда идёт в два шага: предпросмотр от FunPay → явное подтверждение пользователем.
- `open_url` открывает только `https://funpay.com/…` и страницы этого репозитория.
- Все данные с FunPay выводятся в интерфейс через экранирование (`esc()`), HTML из лотов не исполняется.

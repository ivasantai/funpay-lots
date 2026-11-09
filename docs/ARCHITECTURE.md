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
free_translate.py    бесплатный перевод RU→EN через MyMemory (без ключа)
features.py          статистика продаж, цены конкурентов, аренды, бэкап/восстановление лотов
background.py        фоновый поток (автоподнятие, новые заказы/сообщения, аренды), уведомления ОС, трей
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
| `state()` | есть ли сохранённый ключ, версия, настройки, есть ли трей |
| `set_setting(key, value)` | тема, фон, уведомления, параметры аренды |
| `accounts()` / `switch_account(id)` | список аккаунтов / переключение |
| `events()` | события фона для окна (уведомления, обновления) |
| `bulk_edit(node, offer, replace, price)` | замена текста и/или изменение цены одного лота |
| `autoraise_state()` / `autoraise_set(enabled, nodes)` / `raise_now(node)` | автоподнятие |
| `templates()` / `template_save(name, fields)` / `template_delete(id)` | шаблоны описаний |
| `backup_lot(...)` / `backup_save(lots)` / `backup_open()` / `backup_restore(item, inactive)` | бэкап и восстановление |
| `orders(cont, state)` / `order(id)` / `refund(id)` / `review_reply(id, text)` / `rentals()` | заказы и аренды |
| `chats()` / `chat_history(id)` / `send_message(id, text)` | чаты |
| `stats(days)` / `competitors(node)` | аналитика |
| `ai_chat_reply(chat_id, hint)` / `ai_review_reply(order_id, hint)` | черновики ответов нейросетью |
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
| `ai_translate(fields)` | перевести `summary`/`desc`/`payment_msg` на английский; в ответе `engine`: `claude` или `free` |
| `set_translator(mode, email)` | режим перевода `auto`/`free`/`claude` и почта для лимита MyMemory |
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

### Поднятие, заказы, чаты, витрина

| Действие | Запрос |
|---|---|
| ID игры раздела | `GET /lots/<node>/trade` → кнопка `.js-lot-raise[data-game][data-node]` |
| Поднять | `POST /lots/raise` (`game_id`, `node_id`, `node_ids[]` — все ваши разделы этой игры). Ответ `{"error": false, "msg": …}` или `{"error": true, "msg": "Подождите 2 часа."}` (срок разбирает `parse_wait`; «час» без числа = 1 час). Если пришёл `modal` с выбором разделов — повтор со всеми `node_ids[]` из него |
| Продажи | `GET /orders/trade[?state=paid|closed|refunded]`, следующая страница — `POST` с `continue`. `a.tc-item`: класс `info` — ожидает, `warning` — возврат, иначе закрыт; `.tc-order`, `.tc-date-time`, `.order-desc`, `.media-user-name`, `.tc-price` |
| Заказ | `GET /orders/<id>/` → `.param-item` (h5 + значение), `.order-review` (рейтинг `rating<N>`, текст, `.review-compiled-reply`), `.chat[data-id]` — ID чата, `button.btn-refund` — можно вернуть |
| Возврат | `POST /orders/refund` (`id`, `csrf_token`) |
| Ответ на отзыв | `POST /orders/review` (`authorId` = свой ID, `text`, `rating`, `orderId`, `csrf_token`) |
| Список чатов | `POST /runner/` с объектом `chat_bookmarks` → `a.contact-item` (`data-id`, `data-node-msg`, класс `unread`) |
| История чата | `GET /chat/history?node=<id>&last_message=…` → `chat.messages[]` (`id`, `author`, `html`; автор 0 — FunPay) |
| Отправить сообщение | `POST /runner/` с `request: {action: "chat_message", data: {node, last_message: -1, content}}` |
| Витрина раздела | `GET /lots/<node>/` → все `a.tc-item`: `id` из ссылки, `data-user`, `data-online`, `data-f-*` (параметры), `.tc-price[data-s]` — цена для покупателя. Свои лоты идут **без** `data-user` — они отмечаются по ID |

Даты вида «сегодня, 11:52» / «вчера, …» / «2 ноября, …» / «12 октября 2025, …» переводит в unix-время
`parse_date`; срок из названия («НА 3 ЧАСА», «30 минут», «1 месяц») — `parse_duration` (в минутах).

### Аналитика и аренды (`features.py`)
- **Статистика** — по продажам (`/orders/trade`, до 15 страниц, пока не выйдем за период). Возвраты считаются
  отдельно и в выручку не входят. Основная валюта — с наибольшей выручкой. Лоты группируются по названию без
  хвоста «, С подпиской, Pro», который FunPay дописывает к названию в заказе.
- **Конкуренты** — для каждого вашего лота: группа «те же `data-f-*` и тот же срок», место по цене
  (1 + число более дешёвых), минимум, медиана, 5 самых дешёвых. Для выключенных лотов (их нет на витрине) —
  рынок того же срока.
- **Аренды** — заказы (кроме возвратов) со сроком из названия до недели; конец = время заказа + срок +
  бонусные минуты из настроек + ручная поправка по заказу (`accounts[uid].rentals_extra[номер]`, минуты,
  меняется методом `rental_adjust(order_id, minutes)`; при изменении заказ убирается из `rentals_done` /
  `rentals_warned`, чтобы напоминания сработали заново).
- **Бэкап** — все не служебные поля формы каждого лота (`get_form`). Восстановление берёт свежую форму
  раздела, подставляет поля по имени и сохраняет как **новый** лот (по умолчанию выключенным).

### Фон (`background.py`)
`Worker` — поток, просыпается каждые 10 секунд (или сразу по `wake`):
- **автоподнятие** — для всех аккаунтов с включённым автоподнятием; у каждой игры свой срок следующей
  попытки (`autoraise.next[game]` = ответ FunPay + 90 секунд), последняя попытка — в `autoraise.last`;
- **заказы** (раз в минуту) и **чаты** (раз в 30 секунд) — только для открытого аккаунта; первый проход лишь
  запоминает, что уже есть, потом новые оплаченные заказы и непрочитанные сообщения дают уведомление;
- **аренды** — напоминание за 10 минут и по окончании, по желанию автосообщение в чат заказа
  (ID обработанных заказов хранятся, чтобы не повторять).

Уведомления: событие в окно (интерфейс забирает их методом `events()` раз в 5 секунд) + уведомление ОС:
Windows — через значок в трее (pystray), macOS — `osascript display notification`, Linux — `notify-send`.
Закрытие окна при «Работать в фоне»: обработчик `closing` возвращает `False`, окно прячется (Windows, трей)
или сворачивается (macOS/Linux).

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

### Бесплатный перевод (`free_translate.py`)
`GET https://api.mymemory.translated.net/get?q=…&langpair=ru|en[&de=почта]` — публичный API без ключа.
- Лимит запроса — 500 байт, поэтому текст переводится **по строкам** (так же сохраняются переносы),
  длинные строки режутся по предложениям/словам до 450 байт. До 4 запросов параллельно.
- Края строки (маркеры `•`, эмодзи, знаки препинания — всё, что не буквы/цифры) отрезаются до перевода
  и возвращаются после: переводчик их теряет или переставляет.
- Строки без кириллицы и повторяющиеся строки не отправляются (экономия дневного лимита).
- Исчерпанный лимит: `quotaFinished`, статус 429 или текст `MYMEMORY WARNING` → понятная ошибка.
- Выбор движка в `Api.ai_translate`: настройка `translator` (`auto` по умолчанию: Claude при наличии ключа).

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
  "active": "1234567",
  "accounts": {
    "1234567": {
      "golden_key": "…", "username": "MyShop",
      "nodes": {"1355": "Аккаунты ChatGPT", "1392": "Прочее Telegram"},
      "autoraise": {"enabled": true, "nodes": [], "next": {"334": 1794050000}, "last": {"334": {"ok": false, "msg": "Подождите 3 часа."}}},
      "rentals_done": ["ORDER001"], "rentals_warned": []
    }
  },
  "templates": [{"id": "…", "name": "Аренда ChatGPT", "fields": {"fields[desc][ru]": "…"}}],
  "theme": "auto", "close_to_background": false, "notify_orders": true, "rental_msg": "…",
  "anthropic_key": "…", "translator": "auto"
}
```
До 1.6.0 `golden_key` и `nodes` лежали в корне — при первом входе новой версией они переносятся в аккаунт.
Простые настройки интерфейс меняет через `set_setting` (только ключи из `SETTINGS_KEYS` в `app.py`).
Файл пишется атомарно (через `.tmp`), на macOS — с правами `600`. Ключ хранится открытым текстом,
так же как его хранит браузер.

## Безопасность
- Ключ уходит только на `funpay.com`. Кроме FunPay приложение обращается к GitHub
  (`api.github.com` и скачивание релиза) — без ключа и личных данных — и, только по кнопкам ИИ,
  к `api.anthropic.com` (тексты лота и вводные; golden_key туда не отправляется), а по кнопке
  перевода без ключа — к `api.mymemory.translated.net` (только русские строки лота и, если указана, почта).
- Вывод средств всегда идёт в два шага: предпросмотр от FunPay → явное подтверждение пользователем.
- `open_url` открывает только `https://funpay.com/…` и страницы этого репозитория.
- Все данные с FunPay выводятся в интерфейс через экранирование (`esc()`), HTML из лотов не исполняется.

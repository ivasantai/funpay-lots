"""Собирает ui/i18n_en.json — словарь перевода интерфейса на английский.

    python tools/i18n_build.py

Как работает перевод (ui/index.html → tr(), app.py → i18n.tr()):
  1. точное совпадение строки (без пробелов по краям) в EXACT;
  2. первый подходящий шаблон из PATTERNS (регулярка на всю строку; $1, $2 — группы, которые тоже переводятся);
  3. иначе строка режется по « • », « · », «: » и переводится по частям.
Ключ — русский текст в том виде, в каком он появляется на экране (с подставленными числами).
"""
import json
import pathlib

EXACT = {
    # ---------- вход ----------
    "Управление лотами вашего аккаунта FunPay": "Manage the lots of your FunPay account",
    "Ключ аккаунта (golden_key)": "Account key (golden_key)",
    "32 символа из букв и цифр": "32 letters and digits",
    "Показать": "Show",
    "Запомнить на этом компьютере": "Remember on this computer",
    "Войти": "Sign in",
    "Вход…": "Signing in…",
    "Отмена — вернуться к текущему аккаунту": "Cancel — back to the current account",
    "Где взять ключ?": "Where do I get the key?",
    "Откройте funpay.com в браузере и войдите в аккаунт.": "Open funpay.com in your browser and sign in.",
    "Откройте инструменты разработчика (F12 или ⌥⌘I на Mac).": "Open the developer tools (F12, or ⌥⌘I on a Mac).",
    "Скопируйте значение cookie": "Copy the value of the cookie",
    "Ключ даёт полный доступ к аккаунту — не передавайте его никому. Приложение хранит его только локально.":
        "The key gives full access to your account — never share it. The app stores it only on this computer.",
    # ---------- шапка и вкладки ----------
    "Лоты": "Lots", "Заказы": "Orders", "Чаты": "Chats", "Финансы": "Finances", "Аналитика": "Analytics",
    "Аккаунты": "Accounts", "Настройки": "Settings",
    "⚡ Поднятие": "⚡ Raise", "Автоподнятие лотов": "Auto-raise lots", "Бэкап и восстановление": "Backup and restore",
    "＋ Новый лот": "＋ New lot", "Проверить, вышла ли новая версия": "Check whether a new version is out",
    "вкл": "on", "выкл": "off", "сейчас": "now",
    "＋ Добавить аккаунт": "＋ Add account",
    "💾 Сохранить бэкап всех лотов…": "💾 Save a backup of all lots…",
    "📂 Восстановить из бэкапа…": "📂 Restore from backup…",
    # ---------- список лотов ----------
    "Все лоты": "All lots", "Разделы": "Categories", "Поиск по названию…": "Search by title…",
    "Все": "All", "Активные": "Active", "Неактивные": "Inactive",
    "Включить": "Enable", "Выключить": "Disable", "Цена…": "Price…", "Заменить текст…": "Replace text…",
    "Удалить": "Delete", "Снять выделение": "Clear selection",
    "Вкл.": "On", "Название": "Title", "Наличие": "In stock", "Цена": "Price",
    "Редактировать": "Edit", "Открыть на сайте": "Open on the site", "Дублировать": "Duplicate",
    "Ошибка загрузки": "Failed to load", "Убрать раздел из списка": "Remove category from the list",
    "Ничего не найдено": "Nothing found", "В этом разделе нет лотов": "No lots in this category",
    "Лотов пока нет. Нажмите «Новый лот».": "No lots yet. Click “New lot”.",
    "Загружаю лоты…": "Loading lots…", "(без названия)": "(untitled)",
    "Лот включён": "Lot enabled", "Лот выключен": "Lot disabled", "Лот удалён": "Lot deleted",
    "Лот сохранён": "Lot saved", "Лот создан": "Lot created", "Копирую лот…": "Copying the lot…",
    "Удалить лот?": "Delete the lot?", "Удалить лоты?": "Delete the lots?",
    "Выйти": "Sign out", "Выйти из аккаунта?": "Sign out of the account?",
    "Ключ этого аккаунта будет удалён с компьютера.": "This account's key will be removed from this computer.",
    "Отмена": "Cancel", "Закрыть": "Close", "Готово": "Done", "Применить": "Apply", "Сохранить": "Save",
    "Сохранено": "Saved", "Повторить": "Retry", "Далее": "Next", "Назад": "Back", "Позже": "Later",
    "Пропустить": "Skip", "Неизвестная ошибка": "Unknown error",
    # ---------- редактор ----------
    "Редактирование лота": "Edit lot", "Копия лота": "Copy of the lot", "Новый лот": "New lot",
    "Загружаю форму…": "Loading the form…", "Создать лот": "Create lot", "Сохраняю…": "Saving…",
    "Закрыть без сохранения?": "Close without saving?", "Изменения будут потеряны.": "Your changes will be lost.",
    "доп.": "extra", "На сайте это поле появляется в зависимости от других полей":
        "On the site this field appears depending on other fields",
    "Каждая строка — отдельный товар для автовыдачи.": "Each line is a separate item for automatic delivery.",
    "English version": "English version",
    "✨ Заполнить с ИИ": "✨ Fill in with AI", "🌐 Перевести на английский": "🌐 Translate to English",
    "📋 Шаблоны": "📋 Templates", "Что продаёте?": "What are you selling?",
    "Например: аренда личного аккаунта ChatGPT Plus на 3 часа, выдача сразу после оплаты, +1 час за отзыв. Можно коротко — нейросеть сама оформит текст.":
        "For example: rental of a personal ChatGPT Plus account for 3 hours, delivery right after payment, +1 hour for a review. Keep it short — the AI will write the text.",
    "Учтутся раздел, параметры лота и уже написанный текст (как пример вашего стиля).":
        "The category, the lot's parameters and the text you already have (as an example of your style) are taken into account.",
    "Написать сообщение покупателю после оплаты": "Also write the message to the buyer after payment",
    "Сразу сделать английскую версию": "Make the English version too",
    "Сгенерировать": "Generate", "Пишу…": "Writing…", "Перевожу…": "Translating…",
    "Текст готов — проверьте его перед сохранением": "The text is ready — check it before saving",
    "Перевод готов — проверьте перед сохранением": "The translation is ready — check it before saving",
    "Перевод готов (бесплатный переводчик) — проверьте перед сохранением":
        "The translation is ready (free translator) — check it before saving",
    "Сначала добавьте ключ нейросети в настройках": "Add an AI key in the settings first",
    "Шаблоны описаний": "Description templates", "Шаблонов пока нет": "No templates yet",
    "Сохранить текущие тексты лота как шаблон": "Save the lot's current texts as a template",
    "Название шаблона": "Template name", "Шаблон сохранён": "Template saved",
    "Сохраняются краткое и подробное описание и сообщение после оплаты (RU и EN). Применение заменяет эти поля в открытом лоте.":
        "The short and detailed descriptions and the message after payment (RU and EN) are saved. Applying a template replaces these fields in the open lot.",
    # поля формы FunPay
    "Краткое описание": "Short description", "Подробное описание": "Detailed description",
    "Сообщение покупателю после оплаты": "Message to the buyer after payment", "Картинки": "Images",
    "Автоматическая выдача": "Automatic delivery", "Товары": "Items", "Цена за 1 шт.": "Price per unit",
    "Активное": "Active", "Деактивировать после продажи": "Deactivate after sale",
    "Тип подписки": "Subscription type", "С подпиской или без": "With or without subscription",
    "С подпиской": "With subscription", "Без подписки": "Without subscription",
    "Тип предложения": "Offer type", "Сервер": "Server", "Игра": "Game", "Категория": "Category",
    "Редактирование предложения": "Edit offer", "Добавление предложения": "New offer",
    "Заполните все поля": "Fill in all fields", "Заполните это поле": "Fill in this field",
    "Заполните это поле.": "Fill in this field.", "Укажите цену": "Specify the price", "Укажите цену.": "Specify the price.",
    # ---------- новый лот ----------
    "В каком разделе создать лот?": "Which category should the lot go to?",
    "Игра или раздел, например «Telegram» или ID раздела": "Game or category, e.g. “Telegram”, or a category ID",
    "Мои разделы — или начните вводить для поиска по всему каталогу":
        "My categories — or start typing to search the whole catalog",
    "мой раздел": "my category", "по ID": "by ID",
    # ---------- массовые правки ----------
    "Как изменить": "How to change", "Поставить точную цену": "Set an exact price", "Изменить на %": "Change by %",
    "Прибавить / вычесть сумму": "Add / subtract an amount", "Новая цена": "New price",
    "Процент (например 10 или -15)": "Percent (e.g. 10 or -15)", "Сумма (например 1.5 или -2)": "Amount (e.g. 1.5 or -2)",
    "например 5 или -10": "e.g. 5 or -10",
    "Цена — та, что вы получаете (без комиссии FunPay), как в форме лота. Округление до 0.01.":
        "This is the price you receive (without the FunPay fee), as in the lot form. Rounded to 0.01.",
    "Введите число": "Enter a number", "Изменение цен": "Changing prices", "Замена текста": "Replacing text",
    "Найти": "Find", "Заменить на": "Replace with", "Заменить": "Replace", "Что искать?": "What should I look for?",
    "+1 ЧАС ЗА ОТЗЫВ": "+1 HOUR FOR A REVIEW", "+2 ЧАСА ЗА ОТЗЫВ": "+2 HOURS FOR A REVIEW",
    "Заменяется во всех текстах лота: краткое и подробное описание, сообщение после оплаты (русская и английская версии). Регистр учитывается.":
        "Replaced in all of the lot's texts: short and detailed description, message after payment (Russian and English versions). Case-sensitive.",
    # ---------- бэкап ----------
    "Бэкап лотов": "Lot backup", "Нет лотов для бэкапа": "No lots to back up", "Выбрать все": "Select all",
    "заново": "as new", "(существующие не меняются).": "(existing lots are not changed).",
    "Создать выключенными (проверите и включите сами)": "Create them disabled (you check and enable them yourself)",
    "Восстановить": "Restore",
    # ---------- автоподнятие ----------
    "Поднимать лоты автоматически": "Raise lots automatically",
    "Приложение поднимает лоты, как только FunPay это разрешает, и само ждёт нужное время.":
        "The app raises your lots as soon as FunPay allows it and waits the required time by itself.",
    "Раздел": "Category", "Последняя попытка": "Last attempt", "Следующая": "Next", "Поднять": "Raise",
    "Разделы одной игры FunPay поднимает вместе.": "FunPay raises categories of the same game together.",
    "Автоподнятие включено": "Auto-raise enabled", "Автоподнятие выключено": "Auto-raise disabled",
    "Лоты подняты": "Lots raised", "Предложения подняты": "Offers raised", "Подождите час.": "Wait an hour.",
    "Автоподнятие работает, пока приложение запущено. Чтобы оно не выключалось при закрытии окна, включите «Работать в фоне» в ⚙ — окно будет сворачиваться в трей.":
        "Auto-raise works while the app is running. To keep it going when you close the window, turn on “Run in the background” in ⚙ — the window will go to the tray.",
    "Автоподнятие работает, пока приложение запущено. Чтобы оно не выключалось при закрытии окна, включите «Работать в фоне» в ⚙ — окно будет сворачиваться.":
        "Auto-raise works while the app is running. To keep it going when you close the window, turn on “Run in the background” in ⚙ — the window will be minimized.",
    # ---------- заказы и аренды ----------
    "Аренды": "Rentals", "по заказам с «НА N ЧАСОВ» в названии": "from orders with “FOR N HOURS” in the title",
    "Настроить": "Configure", "Сейчас активных аренд нет.": "No active rentals right now.",
    "Покупатель, номер или лот…": "Buyer, order number or lot…",
    "Ожидают": "Pending", "Закрытые": "Closed", "Возвраты": "Refunds",
    "Дата": "Date", "Заказ": "Order", "Покупатель": "Buyer", "Статус": "Status", "Сумма": "Amount",
    "Заказов нет": "No orders", "Загружаю заказы…": "Loading orders…", "Показать ещё": "Show more",
    "Ожидает": "Pending", "Закрыт": "Closed", "Возврат": "Refund", "Оплачен": "Paid", "Открыт": "Opened",
    "Заказ →": "Order →", "Добавить:": "Add:", "+30 мин": "+30 min", "+1 ч": "+1 h",
    "Своё значение, можно убавить": "Custom value, can also subtract", "Добавлено вручную": "Added manually",
    "Часы": "Hours", "Минуты": "Minutes", "Убавить, а не добавить": "Subtract instead of adding",
    "«Сбросить» вернёт срок, рассчитанный по названию лота.": "“Reset” returns the duration calculated from the lot title.",
    "Сбросить": "Reset", "Укажите время больше нуля": "Enter a time greater than zero",
    "Покупатель:": "Buyer:", "Отзыв": "Review", "Отзыва нет": "No review",
    "Ответ на отзыв…": "Reply to the review…", "Изменить ответ…": "Edit the reply…",
    "✨ Черновик ИИ": "✨ AI draft", "Ответить": "Reply", "Обновить ответ": "Update reply",
    "Вернуть деньги": "Refund", "Вернуть деньги?": "Refund the money?", "На сайте ↗": "On the site ↗",
    "Открыть чат": "Open chat", "Деньги возвращены": "Money refunded",
    "Ответ на отзыв опубликован": "Review reply published",
    # ---------- чаты ----------
    "Выберите чат слева": "Select a chat on the left", "Чатов нет": "No chats", "Сообщений нет": "No messages",
    "Сообщение… (Ctrl+Enter — отправить)": "Message… (Ctrl+Enter to send)", "Отправить": "Send",
    "Черновик ответа нейросетью": "Draft a reply with AI", "✨ ИИ": "✨ AI", "🖼 картинка": "🖼 image",
    # ---------- финансы ----------
    "Баланс": "Balance", "Открыть на сайте ↗": "Open on the site ↗", "⟳ Обновить": "⟳ Refresh",
    "Вывести": "Withdraw", "История операций": "Transaction history", "Операция": "Transaction",
    "Операций нет": "No transactions", "Загружаю финансы…": "Loading finances…",
    "Все операции": "All transactions", "Пополнения": "Top-ups", "Выводы": "Withdrawals", "Другое": "Other",
    "Доллары": "Dollars", "Рубли": "Rubles", "Евро": "Euros",
    "Завершено": "Completed", "Отменено": "Cancelled", "Обрабатывается": "Processing", "В обработке": "Processing",
    "Вывод средств": "Withdraw funds", "Счёт": "Account", "Способ вывода": "Withdrawal method", "Банк": "Bank",
    "— выберите банк —": "— select a bank —", "Всё": "All", "Весь баланс": "Whole balance", "К получению": "You receive",
    "Сохранённые реквизиты — в выпадающем списке поля.": "Saved details are in the field's drop-down list.",
    "Проверяю…": "Checking…", "Выберите банк": "Select a bank", "Укажите сумму": "Enter an amount",
    "Проверьте реквизиты: после подтверждения FunPay создаст заявку на вывод, деньги спишутся с баланса.":
        "Check the details: after you confirm, FunPay will create a withdrawal request and debit your balance.",
    "Способ": "Method", "Спишется": "Will be debited", "Код 2FA из приложения-аутентификатора": "2FA code from your authenticator app",
    "Введите код 2FA": "Enter the 2FA code", "Отправляю…": "Sending…", "Заявка на вывод создана": "Withdrawal request created",
    "Банковская карта": "Bank card", "Банковская карта UA": "Bank card (UA)", "СБП": "SBP (Faster Payments)",
    "ЮMoney": "YooMoney", "Номер карты": "Card number", "Телефон для СБП": "Phone number for SBP",
    "Кошелек": "Wallet", "Кошелёк": "Wallet", "Почта аккаунта на Binance": "Binance account email",
    # ---------- аналитика ----------
    "Продажи": "Sales", "Цены конкурентов": "Competitor prices", "Считаю продажи…": "Calculating sales…",
    "Выручка": "Revenue", "Продаж": "Sales", "Средний чек": "Average order", "в основной валюте": "in the main currency",
    "Повторные покупатели": "Repeat buyers", "купили больше 1 раза": "bought more than once",
    "Лучшие лоты": "Top lots", "Продаж за период нет": "No sales in this period", "Лот": "Lot",
    "Смотрю витрину FunPay…": "Looking at the FunPay storefront…", "Нет разделов с лотами": "No categories with lots",
    "Ваш лот": "Your lot", "Срок": "Duration", "Ваша цена": "Your price", "Место": "Rank", "Мин.": "Min",
    "Медиана": "Median", "Дешевле всех ▾": "Cheapest ▾", "выключен — нет на витрине": "disabled — not on the storefront",
    "нет на витрине": "not on the storefront", "продавец": "seller",
    # ---------- настройки ----------
    "Общие": "General", "Тема": "Theme", "Как в системе": "System", "Светлая": "Light", "Тёмная": "Dark",
    "Язык": "Language",
    "Работать в фоне": "Run in the background",
    "Закрытие окна прячет приложение в трей (значок у часов). Выход — через меню значка.":
        "Closing the window hides the app to the tray (icon next to the clock). Quit from the icon's menu.",
    "Закрытие окна сворачивает приложение в Dock/панель задач. Выход — через меню приложения.":
        "Closing the window minimizes the app to the Dock/taskbar. Quit from the app menu.",
    "Нужно, чтобы автоподнятие и уведомления работали при закрытом окне.":
        "Needed for auto-raise and notifications to keep working while the window is closed.",
    "Горячие клавиши: Ctrl/⌘+1…5 — вкладки, Ctrl/⌘+N — новый лот, Ctrl/⌘+F — поиск, Ctrl/⌘+R — обновить, Esc — закрыть окно.":
        "Hotkeys: Ctrl/⌘+1…5 — tabs, Ctrl/⌘+N — new lot, Ctrl/⌘+F — search, Ctrl/⌘+R — refresh, Esc — close a window.",
    "Обновления": "Updates", "Установлена версия": "Installed version", "⟳ Проверить сейчас": "⟳ Check now",
    "Проверять автоматически каждые 30 минут": "Check automatically every 30 minutes",
    "Пока приложение запущено, в том числе в фоне. О новой версии придёт уведомление.":
        "While the app is running, including in the background. You'll get a notification about a new version.",
    "Уведомления": "Notifications", "Новые заказы": "New orders", "Новые сообщения в чатах": "New chat messages",
    "Каждое успешное автоподнятие": "Every successful auto-raise", "Аренда": "Rental",
    "Срок аренды берётся из названия лота («НА 3 ЧАСА», «НА 30 МИНУТ»), отсчёт — от времени заказа.":
        "The rental duration is taken from the lot title (“НА 3 ЧАСА”, “НА 30 МИНУТ”), counted from the order time.",
    "Напоминать за 10 минут до конца и по окончании аренды": "Remind me 10 minutes before and when a rental ends",
    "Бонусные минуты к сроку (например, 60 за отзыв)": "Bonus minutes added to the duration (e.g. 60 for a review)",
    "Автоматически писать покупателю, когда аренда закончилась": "Automatically message the buyer when a rental ends",
    "Текст сообщения ({buyer} — ник покупателя, {order} — номер заказа)":
        "Message text ({buyer} — buyer's nickname, {order} — order number)",
    "Нейросеть (Claude)": "AI (Claude)",
    "Нужна для «✨ Заполнить с ИИ» и для качественного перевода. Используется ключ Anthropic API — оплата по факту использования на вашем аккаунте Anthropic (одно описание обычно стоит доли цента–пару центов).":
        "Needed for “✨ Fill in with AI” and for high-quality translation. Uses an Anthropic API key — pay-as-you-go on your Anthropic account (one description usually costs a fraction of a cent to a couple of cents).",
    "Ключ Anthropic API": "Anthropic API key", "Создать ключ:": "Create a key:",
    ". Хранится только на этом компьютере.": ". Stored only on this computer.",
    "Удалить ключ": "Delete key", "Проверить и сохранить ключ": "Check and save key", "Вставьте ключ": "Paste the key",
    "Ключ нейросети удалён": "AI key deleted",
    "Перевод на английский": "Translation to English", "Автоматически": "Automatic",
    "Нейросеть, если добавлен ключ; без ключа — бесплатный переводчик.": "AI if a key is added; without a key — the free translator.",
    "Всегда бесплатный переводчик (MyMemory)": "Always the free translator (MyMemory)",
    "Без ключа и оплаты, но проще по качеству. Лимит около 5 000 символов в день.":
        "No key or payment, but lower quality. Limit of about 5,000 characters per day.",
    "Всегда нейросеть": "Always AI", "Лучшее качество, нужен ключ Anthropic.": "Best quality, needs an Anthropic key.",
    "Почта для бесплатного переводчика": "Email for the free translator", "(необязательно)": "(optional)",
    "С почтой MyMemory поднимает дневной лимит примерно до 50 000 символов. Почта отправляется только в MyMemory вместе с запросами перевода.":
        "With an email MyMemory raises the daily limit to about 50,000 characters. The email is sent only to MyMemory along with translation requests.",
    "Сохранить настройки перевода": "Save translation settings", "Настройки перевода сохранены": "Translation settings saved",
    # ---------- обновления ----------
    "Обновить": "Update", "Скачать": "Download", "Скачиваю…": "Downloading…", "Перезапуск…": "Restarting…",
    # ---------- сообщения Python ----------
    "В чате нет сообщений, на которые можно ответить.": "There are no messages in the chat to reply to.",
    "Ключ Anthropic не подошёл — проверьте его в настройках (⚙).": "The Anthropic key was rejected — check it in the settings (⚙).",
    "Ключ не подошёл: Anthropic его не принял.": "The key didn't work: Anthropic rejected it.",
    "На аккаунте Anthropic закончились средства — пополните баланс в console.anthropic.com.":
        "Your Anthropic account is out of credit — top it up at console.anthropic.com.",
    "Нейросеть вернула ответ в неожиданном формате. Попробуйте ещё раз.": "The AI returned an unexpected format. Try again.",
    "Нейросеть вернула пустой ответ.": "The AI returned an empty answer.",
    "Нейросеть отказалась писать такой текст. Переформулируйте вводные.": "The AI refused to write this text. Rephrase your input.",
    "Нет связи с api.anthropic.com.": "Can't reach api.anthropic.com.",
    "Нечего переводить: русские поля пустые.": "Nothing to translate: the Russian fields are empty.",
    "Опишите, что продаёте: пара фраз о товаре, условиях и выдаче.": "Describe what you sell: a couple of sentences about the item, terms and delivery.",
    "Ответ получился слишком длинным. Сократите вводные.": "The answer came out too long. Shorten your input.",
    "Слишком много запросов к нейросети — подождите минуту.": "Too many AI requests — wait a minute.",
    "У заказа нет отзыва.": "The order has no review.",
    "У ключа Anthropic нет доступа к модели.": "The Anthropic key has no access to the model.",
    "У ключа нет доступа к модели.": "The key has no access to the model.",
    "Укажите ключ Anthropic API в настройках (⚙).": "Enter an Anthropic API key in the settings (⚙).",
    "FunPay Lots работает в фоне": "FunPay Lots is running in the background",
    "Значок — в области уведомлений. Выход — через его меню.": "The icon is in the notification area. Quit from its menu.",
    "В шаблоне нет текста.": "The template has no text.", "Введите golden_key.": "Enter your golden_key.",
    "Для этого аккаунта не сохранён ключ — войдите заново.": "No key is saved for this account — sign in again.",
    "Назовите шаблон.": "Name the template.", "Не удалось прочитать файл.": "Couldn't read the file.",
    "Неверный номер заказа.": "Invalid order number.", "Неизвестная настройка.": "Unknown setting.",
    "Неизвестный режим перевода.": "Unknown translation mode.", "Нет доступного обновления.": "No update available.",
    "Почта для переводчика указана неверно.": "The translator email is invalid.",
    "Сначала войдите по ключу.": "Sign in with your key first.", "Укажите число минут.": "Enter a number of minutes.",
    "Аренда закончилась": "Rental ended", "Аренда скоро закончится": "Rental ends soon",
    "Откройте приложение и нажмите «Обновить».": "Open the app and click “Update”.",
    "Это не файл бэкапа FunPay Lots.": "This is not a FunPay Lots backup file.",
    "Дневной лимит бесплатного перевода исчерпан. Попробуйте завтра, укажите почту в ⚙ (лимит станет в 10 раз больше) или добавьте ключ нейросети.":
        "The free translation limit for today is used up. Try tomorrow, add an email in ⚙ (the limit becomes 10 times higher) or add an AI key.",
    "Нечего переводить: в русских полях нет текста на русском.": "Nothing to translate: there's no Russian text in the Russian fields.",
    "FunPay вернул неожиданный ответ чата.": "FunPay returned an unexpected chat response.",
    "FunPay не отдал форму лота (лот удалён или нет доступа к разделу).": "FunPay didn't return the lot form (the lot was deleted or you have no access to the category).",
    "FunPay не смог посчитать сумму к получению.": "FunPay couldn't calculate the amount you receive.",
    "FunPay отклонил запрос (403). Возможно, ключ устарел — зайдите на сайт и возьмите новый golden_key.":
        "FunPay rejected the request (403). The key may be outdated — open the site and get a new golden_key.",
    "Ключ выглядит неверно: golden_key — это строка из латиницы и цифр (обычно 32 символа).":
        "The key looks wrong: golden_key is a string of Latin letters and digits (usually 32 characters).",
    "Ключ не подошёл: FunPay не узнал аккаунт. Проверьте golden_key.": "The key didn't work: FunPay didn't recognize the account. Check your golden_key.",
    "Не удалось загрузить чат.": "Couldn't load the chat.",
    "Не удалось прочитать страницу FunPay — возможно, сайт изменился.": "Couldn't read the FunPay page — the site may have changed.",
    "Не удалось прочитать страницу «Финансы» — возможно, FunPay изменил сайт.": "Couldn't read the “Finances” page — FunPay may have changed the site.",
    "Неверное значение цены.": "Invalid price.", "Ответ на отзыв пустой.": "The review reply is empty.",
    "Пустое сообщение.": "Empty message.", "Сообщение не доставлено.": "The message wasn't delivered.",
    "Автообновление на этой ОС не поддерживается.": "Auto-update isn't supported on this OS.",
    "Автоустановка доступна только в собранной версии приложения.": "Automatic installation is only available in the built app.",
    "В архиве обновления нет приложения.": "The update archive doesn't contain the app.",
    "Не удалось найти .app приложения.": "Couldn't find the app's .app bundle.",
    "Релизы не найдены (репозиторий недоступен).": "No releases found (the repository is unavailable).",
    "Скачанный файл повреждён.": "The downloaded file is damaged.",
    "Закрытие окна прячет приложение в трей (значок у часов). Выход — через меню значка. Нужно, чтобы автоподнятие и уведомления работали при закрытом окне.":
        "Closing the window hides the app to the tray (icon next to the clock). Quit from the icon's menu. Needed for auto-raise and notifications to keep working while the window is closed.",
    "Закрытие окна сворачивает приложение в Dock/панель задач. Выход — через меню приложения. Нужно, чтобы автоподнятие и уведомления работали при закрытом окне.":
        "Closing the window minimizes the app to the Dock/taskbar. Quit from the app menu. Needed for auto-raise and notifications to keep working while the window is closed.",
    "Как в системе / System": "System", "Язык / Language": "Language / Язык",
    # частые слова в названиях разделов FunPay
    "Аккаунты": "Accounts", "Прочее": "Other", "Подписка": "Subscription", "Прочее для прочих игр": "Other for other games",
    "Ключи": "Keys", "Услуги": "Services", "Предметы": "Items", "Валюта": "Currency", "Буст": "Boosting",
    "Открыть FunPay Lots": "Open FunPay Lots", "Поднять лоты сейчас": "Raise lots now",
    "Проверить обновления": "Check for updates", "Выход": "Quit",
    "Внутренняя ошибка": "Internal error", "FunPay отклонил сохранение": "FunPay rejected the save",
    "FunPay не поднял лоты": "FunPay didn't raise the lots",
}

PATTERNS = [
    # числа и единицы
    (r"^(\d+) шт\.$", "$1 pcs"),
    (r"^(\d+(?:\.\d+)?) дн\.$", "$1 d"), (r"^(\d+(?:\.\d+)?) ч$", "$1 h"), (r"^(\d+) мин$", "$1 min"),
    (r"^(\d+) ч (\d+) мин$", "$1 h $2 min"), (r"^через (.+)$", "in $1"),
    (r"^закончилась (.+) назад$", "ended $1 ago"), (r"^до (.+)$", "until $1"),
    (r"^Выбрано: (\d+)$", "Selected: $1"), (r"^Удалено: (\d+)$", "Deleted: $1"),
    (r"^Включено: (\d+)$", "Enabled: $1"), (r"^Выключено: (\d+)$", "Disabled: $1"),
    (r"^Создано лотов: (\d+)$", "Lots created: $1"),
    (r"^Изменено: (\d+) · без изменений: (\d+) · ошибок: (\d+)$", "Changed: $1 · unchanged: $2 · errors: $3"),
    (r"^Изменено: (\d+) · без изменений: (\d+)$", "Changed: $1 · unchanged: $2"),
    (r"^Цена: (\d+) лот\(ов\)$", "Price: $1 lot(s)"), (r"^Замена текста: (\d+) лот\(ов\)$", "Replace text: $1 lot(s)"),
    (r"^«(.+)» будет удалён с FunPay без возможности восстановления\.$", "“$1” will be deleted from FunPay permanently."),
    (r"^(\d+) лотов будут удалены с FunPay без возможности восстановления\.$", "$1 lots will be deleted from FunPay permanently."),
    (r"^Читаю лоты: (\d+) / (\d+)$", "Reading lots: $1 / $2"), (r"^(\d+) / (\d+)$", "$1 / $2"),
    (r"^Бэкап сохранён: (\d+) лотов$", "Backup saved: $1 lots"),
    (r"^Восстановление: (\d+) лотов$", "Restore: $1 lots"),
    (r"^Бэкап (.*) от (.+)\. Лоты будут созданы$", "Backup of $1 from $2. The lots will be created"),
    (r"^Аккаунт: (.+)$", "Account: $1"), (r"^Выйти из (.+)$", "Sign out of $1"), (r"^аккаунта$", "the account"),
    (r"^Не удалось загрузить: (.+)$", "Failed to load: $1"),
    (r"^Шаблон «(.+)» применён$", "Template “$1” applied"), (r"^Ключ сохранён · (.+)$", "Key saved · $1"),
    (r"^Раздел #(\d+)$", "Category #$1"), (r"^Раздел (\d+)$", "Category $1"),
    (r"^Картинок у лота: (\d+) \(сохраняются как есть; менять картинки — на сайте\)\.$",
     "Images in the lot: $1 (kept as they are; change images on the site)."),
    (r"^· (.+)$", "· $1"),
    # «Аккаунты ChatGPT» → «ChatGPT Accounts»; только если в строке нет разделителей (иначе — разбор по частям)
    (r"^(Аккаунты|Прочее|Подписка|Ключи|Услуги|Предметы|Валюта|Буст) ([^·•—:,]+)$", "$2 $1"),
    (r"^([^·•—:,]+), (Аккаунты|Прочее|Подписка|Ключи|Услуги|Предметы|Валюта|Буст)$", "$1, $2"),
    # автоподнятие и ответы FunPay
    (r"^Подождите (\d+) час(?:а|ов)?\.?$", "Wait $1 h."), (r"^Подождите (\d+) минут(?:у|ы)?\.?$", "Wait $1 min."),
    (r"^Подождите (\d+) час(?:а|ов)? (\d+) минут(?:у|ы)?\.?$", "Wait $1 h $2 min."),
    # заказы и аренды
    (r"^Заказ #(\S+)$", "Order #$1"), (r"^Время аренды #(\S+)$", "Rental time #$1"),
    (r"^Добавлено (.+) к аренде #(\S+)$", "Added $1 to rental #$2"), (r"^Убрано (.+) из аренды #(\S+)$", "Removed $1 from rental #$2"),
    (r"^(.*) · срок по лоту (.+), вручную уже (.+)$", "$1 · lot duration $2, already adjusted by $3"),
    (r"^(.*) · срок по лоту (.+)$", "$1 · lot duration $2"),
    (r"^Покупатель (.+) получит деньги за заказ #(\S+)\. Это нельзя отменить; отзыв покупателя может быть удалён\.$",
     "Buyer $1 will get the money back for order #$2. This can't be undone; the buyer's review may be removed."),
    (r"^Ваш ответ: (.+)$", "Your reply: $1"),
    (r"^Новый заказ #(\S+)$", "New order #$1"), (r"^Сообщение от (.+)$", "Message from $1"),
    (r"^#(\S+) (.+): осталось (\d+) мин$", "#$1 $2: $3 min left"),
    (r"^Доступна FunPay Lots (.+)$", "FunPay Lots $1 is available"),
    # финансы
    (r"^Вывод денег #(\d+)$", "Withdrawal #$1"), (r"^Отмена вывода денег #(\d+)$", "Withdrawal cancelled #$1"),
    (r"^Пополнение баланса #(\d+)$", "Balance top-up #$1"),
    (r"^Россия: комиссия (.+?), но не менее (.+)$", "Russia: fee $1, minimum $2"),
    (r"^Комиссия (.+?), но не менее (.+?); курс (.+)$", "Fee $1, minimum $2; rate $3"),
    (r"^Комиссия (.+?), но не менее (.+)$", "Fee $1, minimum $2"),
    (r"^Сумма, (.+)$", "Amount, $1"), (r"^К получению, (.+)$", "You receive, $1"),
    (r"^Укажите: (.+)$", "Enter: $1"), (r"^Вывести (.+)$", "Withdraw $1"),
    # аналитика
    (r"^за (\d+) дн\., без возвратов$", "for $1 days, without refunds"), (r"^(\d+) покупател(?:ей|я|ь)$", "$1 buyers"),
    (r"^(\d+) дней$", "$1 days"), (r"^Выручка по дням, (.+)$", "Revenue by day, $1"),
    (r"^продаж: (\d+) · возвратов: (\d+)$", "sales: $1 · refunds: $2"), (r"^продаж: (\d+)$", "sales: $1"),
    (r"^из (\d+)$", "of $1"), (r"^(.+) без ком\.$", "$1 without fee"),
    (r"^Предложений в разделе: (\d+)\. Цены — как их видят покупатели \(с комиссией FunPay\)\. Сравнение — с предложениями с теми же параметрами раздела и тем же сроком \(срок берётся из названия\)\. Место 1 — самый дешёвый\.$",
     "Offers in the category: $1. Prices are as buyers see them (with the FunPay fee). Compared with offers that have the same category parameters and the same duration (taken from the title). Rank 1 is the cheapest."),
    # обновления
    (r"^Доступна версия (.+)$", "Version $1 is available"), (r"^Сейчас установлена (.+)$", "Currently installed $1"),
    (r"^(.+) МБ$", "$1 MB"), (r"^У вас последняя версия \((.+)\)$", "You have the latest version ($1)"),
    (r"^Последняя проверка: (.+)$", "Last check: $1"),
    # ошибки с подробностями
    (r"^Внутренняя ошибка: (.+)$", "Internal error: $1"),
    (r"^Нейросеть отклонила запрос: (.+)$", "The AI rejected the request: $1"),
    (r"^Ошибка Anthropic API \((\d+)\): (.+)$", "Anthropic API error ($1): $2"),
    (r"^Бесплатный переводчик не смог перевести текст \((.+)\)\.$", "The free translator couldn't translate the text ($1)."),
    (r"^Бесплатный переводчик ответил ошибкой \((.+)\)\.$", "The free translator returned an error ($1)."),
    (r"^Нет связи с бесплатным переводчиком: (.+)$", "Can't reach the free translator: $1"),
    (r"^FunPay вернул ошибку (\d+) на (.+)$", "FunPay returned error $1 for $2"),
    (r"^В разделе (\d+) нет кнопки поднятия\.$", "Category $1 has no raise button."),
    (r"^Не удалось отправить ответ: (.+)$", "Couldn't send the reply: $1"),
    (r"^Не удалось поднять лоты: (.+)$", "Couldn't raise the lots: $1"),
    (r"^Неожиданный ответ FunPay \((\d+)\): (.+)$", "Unexpected FunPay response ($1): $2"),
    (r"^Неожиданный ответ FunPay: (.+)$", "Unexpected FunPay response: $1"),
    (r"^Нет связи с FunPay: (.+)$", "Can't reach FunPay: $1"),
    (r"^Раздел (\d+) не найден или недоступен для продажи\.$", "Category $1 not found or not available for selling."),
    (r"^Сообщение не доставлено: (.+)$", "The message wasn't delivered: $1"),
    (r"^Цена лота #(\d+) получилась бы нулевой или отрицательной — лот пропущен\.$", "The price of lot #$1 would be zero or negative — lot skipped."),
    (r"^GitHub ответил (\d+) при проверке обновлений\.$", "GitHub returned $1 while checking for updates."),
    (r"^Не удалось проверить обновления: (.+)$", "Couldn't check for updates: $1"),
    (r"^Не удалось скачать обновление: (.+)$", "Couldn't download the update: $1"),
    (r"^Не удалось установить обновление в (.+) \((.+)\)\. Перенесите приложение в «Программы» и попробуйте снова\.$",
     "Couldn't install the update to $1 ($2). Move the app to Applications and try again."),
    (r"^Нет прав на запись в папку (.+)\. Переместите приложение, например, на рабочий стол\.$",
     "No write permission for $1. Move the app, for example, to the desktop."),
    (r"^Нет прав на запись в папку (.+)\.$", "No write permission for $1."),
]

# даты и «N … назад», как их пишет FunPay
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
EN_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PATTERNS += [(r"^сегодня, (\d{1,2}:\d{2})$", "today, $1"), (r"^вчера, (\d{1,2}:\d{2})$", "yesterday, $1")]
EXACT.update({"сегодня": "today", "вчера": "yesterday", "только что": "just now", "назад": "ago"})
for ru, en in zip(MONTHS, EN_MON):
    PATTERNS += [
        (rf"^(\d{{1,2}}) {ru} (\d{{4}}), (\d{{1,2}}:\d{{2}})$", f"{en} $1, $2, $3"),
        (rf"^(\d{{1,2}}) {ru}, (\d{{1,2}}:\d{{2}})$", f"{en} $1, $2"),
        (rf"^(\d{{1,2}}) {ru}$", f"{en} $1"),
    ]
PATTERNS += [
    (r"^(\d+) (?:секунду|секунды|секунд) назад$", "$1 sec ago"),
    (r"^(\d+) (?:минуту|минуты|минут) назад$", "$1 min ago"), (r"^минуту назад$", "a minute ago"),
    (r"^(\d+) (?:час|часа|часов) назад$", "$1 h ago"), (r"^час назад$", "an hour ago"),
    (r"^(\d+) (?:день|дня|дней) назад$", "$1 days ago"), (r"^день назад$", "a day ago"),
    (r"^(\d+) (?:месяц|месяца|месяцев) назад$", "$1 months ago"), (r"^месяц назад$", "a month ago"),
    (r"^(\d+) (?:год|года|лет) назад$", "$1 years ago"),
]

out = pathlib.Path(__file__).resolve().parent.parent / "ui" / "i18n_en.json"
out.write_text(json.dumps({"exact": EXACT, "patterns": PATTERNS}, ensure_ascii=False, indent=0), encoding="utf-8")
print(f"{out.name}: {len(EXACT)} phrases, {len(PATTERNS)} patterns")

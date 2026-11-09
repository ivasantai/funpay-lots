// Мок API для просмотра интерфейса в обычном браузере: ui/index.html?mock
(() => {
  const ok = data => new Promise(r => setTimeout(() => r({ ok: true, data }), 250));
  const cats = [
    { node: 1355, name: "Аккаунты ChatGPT", error: null, game: 334, lots: [
      { id: 101, node: 1355, title: "ChatGPT Plus — аренда на 3 часа, личный аккаунт", server: "", amount: "1", price: "5", unit: "$", active: true },
      { id: 102, node: 1355, title: "ChatGPT Plus — аренда на 6 часов", server: "", amount: "1", price: "8", unit: "$", active: false },
    ]},
    { node: 1392, name: "Прочее Telegram", error: null, game: 224, lots: [
      { id: 201, node: 1392, title: "Telegram Mini App под ключ", server: "", amount: "999 999", price: "12.87", unit: "$", active: true },
    ]},
  ];
  const form = (node, offer) => ({ node, offer: offer || 0, title: "Редактирование предложения", fields: [
    { name: "csrf_token", kind: "system", value: "x" }, { name: "offer_id", kind: "system", value: String(offer || 0) },
    { name: "fields[type]", label: "Тип подписки", kind: "select", locale: "", conditional: true,
      options: [{ value: "", text: "" }, { value: "Plus", text: "Plus" }, { value: "Pro", text: "Pro" }], value: offer ? "Plus" : "" },
    { name: "fields[summary][ru]", label: "Краткое описание", kind: "text", locale: "ru", value: offer ? "ChatGPT Plus — аренда" : "" },
    { name: "fields[summary][en]", label: "Short description", kind: "text", locale: "en", value: "" },
    { name: "fields[desc][ru]", label: "Подробное описание", kind: "textarea", locale: "ru", value: offer ? "Описание лота" : "" },
    { name: "fields[desc][en]", label: "Detailed description", kind: "textarea", locale: "en", value: "" },
    { name: "auto_delivery", label: "Автоматическая выдача", kind: "checkbox", locale: "", value: false },
    { name: "secrets", label: "Товары", kind: "textarea", locale: "", value: "" },
    { name: "price", label: "Цена за 1 шт.", kind: "text", locale: "", value: offer ? "5" : "" },
    { name: "amount", label: "Наличие", kind: "text", locale: "", value: offer ? "1" : "" },
    { name: "active", label: "Активное", kind: "checkbox", locale: "", value: true },
  ]});
  const now = Date.now() / 1000;
  const rentExtra = {};
  const settings = { auto_update_check: true, theme: "auto", close_to_background: false, notify_orders: true, notify_chats: true, notify_raise: false,
    rental_notify: true, rental_auto_msg: false, rental_bonus: 0, rental_msg: "Здравствуйте, {buyer}! Аренда по заказу #{order} закончилась." };
  const orders = [
    { id: "ORDER001", date: "сегодня, 11:52", ts: now - 3600, title: "ChatGPT Plus — аренда НА 3 ЧАСА, С подпиской, Plus", category: "ChatGPT, Аккаунты", buyer: "buyer1", buyer_id: 1, status: "closed", status_text: "Закрыт", amount: "5.00", unit: "$" },
    { id: "ORDER002", date: "сегодня, 10:20", ts: now - 7000, title: "Claude PRO НА 1 ЧАС", category: "Claude, Аккаунты", buyer: "buyer2", buyer_id: 2, status: "paid", status_text: "Оплачен", amount: "3.50", unit: "$" },
    { id: "ORDER003", date: "вчера, 16:27", ts: now - 86400, title: "Claude PRO НА 3 ЧАСА", category: "Claude, Аккаунты", buyer: "buyer3", buyer_id: 3, status: "refunded", status_text: "Возврат", amount: "5.00", unit: "$" },
  ];
  const byDay = Array.from({ length: 30 }, (_, i) => { const d = new Date(Date.now() - (29 - i) * 864e5).toISOString().slice(0, 10);
    const v = [0, 3.5, 5, 0, 12, 7, 0, 21.5, 3.5, 0][i % 10]; return { date: d, revenue: v ? { "$": v } : {}, orders: v ? Math.ceil(v / 5) : 0, refunds: i % 9 === 0 ? 1 : 0 }; });
  window.MOCK_API = {
    state: () => ok({ has_key: false, version: "mock", settings, tray: true, platform: "win32" }),
    events: () => ok([]),
    set_setting: (k, v) => { settings[k] = v; return ok(v); },
    accounts: () => ok([{ id: "1", username: "DemoSeller", active: true, saved: true, autoraise: true }, { id: "2", username: "SecondShop", active: false, saved: true, autoraise: false }]),
    switch_account: () => ok({ id: 2, username: "SecondShop", balance: "3 $" }),
    autoraise_state: () => ok({ enabled: true, nodes: [1355, 1392], background: false,
      next: { "334": now + 5400, "224": now + 1200 }, last: { "334": { ts: now - 9000, ok: true, msg: "Предложения подняты", node: 1355 }, "224": { ts: now - 2400, ok: false, msg: "Подождите час.", node: 1392 } } }),
    autoraise_set: () => ok(true),
    raise_now: () => ok({ ok: false, msg: "Подождите 2 часа.", wait: 7200, game: 334 }),
    templates: () => ok([{ id: "t1", name: "Аренда ChatGPT", fields: { "fields[summary][ru]": "ChatGPT Plus — аренда", "fields[desc][ru]": "Описание по шаблону" } }]),
    template_save: (n, f) => ok([{ id: "t1", name: n, fields: f }]),
    template_delete: () => ok([]),
    bulk_edit: () => ok({ changed: true, price: "6" }),
    backup_lot: (n, o, c) => ok({ node: n, offer: o, category: c, title: "Лот " + o, fields: { "fields[summary][ru]": "Лот " + o } }),
    backup_save: () => ok("C:/demo.json"),
    backup_open: () => ok({ path: "C:/demo.json", account: "DemoSeller", created: "2026-11-07 12:00", lots: [{ node: 1355, title: "Лот из бэкапа", category: "Аккаунты ChatGPT", fields: {} }] }),
    backup_restore: () => ok({ done: true, skipped_fields: [] }),
    orders: () => ok({ items: orders, next: "" }),
    order: id => ok({ id, status: "Закрыт", buyer: "buyer3", chat_id: 77, can_refund: true,
      params: [{ name: "Категория", value: "Аккаунты" }, { name: "Краткое описание", value: "Claude PRO НА 3 ЧАСА" }, { name: "Сумма", value: "5 $" }],
      review: { rating: 4, text: "Всё отлично, быстро выдали", reply: "", can_reply: true } }),
    refund: () => ok({ done: true }), review_reply: () => ok({ done: true }),
    rentals: () => ok([[orders[0], 180, 7200], [orders[1], 60, 300]].map(([o, min, left]) => { const ex = rentExtra[o.id] || 0;
      return { ...o, minutes: min, extra: ex, total: min + ex, end: now + left + ex * 60, left: left + ex * 60, active: true }; })),
    rental_adjust: (id, m) => { rentExtra[id] = (rentExtra[id] || 0) + m; return ok(rentExtra[id]); },
    chats: () => ok([{ id: 77, name: "buyer1", last: "есть в наличии что то?", time: "10:12", unread: true, msg_id: 5 }, { id: 78, name: "buyer3", last: "Спасибо!", time: "вчера", unread: false, msg_id: 3 }]),
    chat_history: id => ok({ id, messages: [
      { id: 1, author: 0, mine: false, system: true, name: null, time: "09:00", text: "Покупатель оплатил заказ #ORDER001." },
      { id: 2, author: 5, mine: false, system: false, name: "buyer1", time: "09:01", text: "Здравствуйте! Когда выдадите?" },
      { id: 3, author: 1, mine: true, system: false, name: "DemoSeller", time: "09:02", text: "Добрый день, уже отправил данные 👍" }] }),
    send_message: () => ok({ done: true }),
    ai_chat_reply: () => ok({ text: "Здравствуйте! Да, в наличии есть — оформляйте заказ, выдам сразу." }),
    ai_review_reply: () => ok({ text: "Спасибо за отзыв! Рады, что всё понравилось 🙌" }),
    stats: days => ok({ days, unit: "$", avg: 17.93, buyers: 12, repeat_buyers: 3, totals: { revenue: { "$": 412.5 }, orders: 23, refunds: 3, refund_sum: { "$": 15 } },
      by_day: byDay.slice(-days), top: [{ title: "CLAUDE x5 MAX 1 МЕСЯЦ", orders: 1, revenue: { "$": 155 }, category: "Claude, Аккаунты" }, { title: "Claude PRO НА 1 ЧАС", orders: 7, revenue: { "$": 21.5 }, category: "Claude, Аккаунты" }] }),
    competitors: node => ok({ node, total_offers: 1126, rows: [
      { id: 101, title: "ChatGPT Plus — аренда НА 3 ЧАСА", visible: true, minutes: 180, my_price: 5.6, unit: "$", rivals: 41, rank: 9, min: 1.2, median: 4.8,
        cheapest: [{ id: 9, price: 1.2, unit: "$", seller: "cheapShop", online: true, title: "ChatGPT Plus 3 часа" }] },
      { id: 102, title: "ChatGPT Plus — аренда НА 6 ЧАСОВ", visible: false, active: false, minutes: 360, my_price: null, seller_price: "8", unit: "$", rivals: 12, rank: null, min: 3, median: 7.5, cheapest: [] }] }),
    login: () => ok({ id: 1, username: "DemoSeller", balance: "50 $" }),
    logout: () => ok(true),
    lots: () => ok(cats),
    games: () => ok([{ game: "ChatGPT", subs: [{ node: 1355, name: "Аккаунты" }, { node: 3559, name: "Подписка" }] },
                     { game: "Telegram", subs: [{ node: 1392, name: "Прочее" }] }]),
    form: (n, o) => ok(form(n, o)),
    save: () => ok({ done: true }),
    delete: () => ok({ done: true }),
    set_active: () => ok({ done: true }),
    forget_category: () => ok(true),
    finance: () => ok({
      balances: [
        { id: "usd", name: "Доллары", value: "50.00 $", unit: "$", channels: [
          { id: "card_usd", name: "Банковская карта", fee: "Россия: комиссия 3%, но не менее 2.75 $" },
          { id: "fps", name: "СБП", fee: "Комиссия 3%, но не менее 1 $; курс 84.327" },
          { id: "usdt_trc", name: "USDT TRC20", fee: "Комиссия 6%, но не менее 1.5 $" }] },
        { id: "rub", name: "Рубли", value: "120.00 ₽", unit: "₽", channels: [{ id: "card_rub", name: "Банковская карта", fee: "Комиссия 3%, но не менее 30 ₽" }] },
        { id: "eur", name: "Евро", value: "0 €", unit: "€", channels: [{ id: "card_eur", name: "Банковская карта", fee: "" }] },
      ],
      ext: {
        card_usd: { name: "Банковская карта", unit: "$", wallet_name: "Номер карты", wallets: ["2200 **** **** 1234"] },
        card_rub: { name: "Банковская карта", unit: "₽", wallet_name: "Номер карты", wallets: [] },
        card_eur: { name: "Банковская карта", unit: "€", wallet_name: "Номер карты", wallets: [] },
        fps: { name: "СБП", unit: "₽", wallet_name: "Телефон для СБП", wallets: [] },
        usdt_trc: { name: "USDT TRC20", unit: "USDT", wallet_name: "Кошелек", wallets: ["TXyz…demo"] },
      },
      banks: [{ id: "1", name: "Сбербанк" }, { id: "2", name: "Т-Банк" }],
      filters: [{ id: "", name: "Все операции" }, { id: "payment", name: "Пополнения" }, { id: "withdraw", name: "Выводы" }, { id: "order", name: "Заказы" }, { id: "other", name: "Другое" }],
    }),
    transactions: (f, c) => ok({ next: c ? "" : "p2", items: [
      { id: "1", date: "сегодня, 11:52", ago: "3 часа назад", title: "Заказ #ORDER001", status: "Завершено", state: "complete", amount: "+ 3.50 $", sign: "+", order: "ORDER001" },
      { id: "2", date: "вчера, 22:11", ago: "16 часов назад", title: "Вывод денег #10000001", status: "Завершено", state: "complete", amount: "− 35.00 $", sign: "-", order: "" },
      { id: "3", date: "2 ноября, 10:03", ago: "4 дня назад", title: "Отмена вывода денег #10000002", status: "Отменено", state: "cancel", amount: "+ 35.00 $", sign: "+", order: "" },
    ]}),
    withdraw_calc: (cur, m, a) => ok({ amount_int: 0, amount_ext: Math.max(0, +(parseFloat(a) * 0.97).toFixed(2)) }),
    withdraw_preview: (cur, m, w, a) => ok({ wallet: w, amount_int: a, amount_ext: (parseFloat(a) * 0.97).toFixed(2), bank: "", twofactor: true }),
    withdraw_confirm: () => ok({ done: true }),
    check_update: () => ok({ current: "1.2.0", latest: "1.3.0", available: true, notes: "- Пример заметок к релизу", url: "", download: "", size: 14000000, can_install: true }),
    skip_update: () => ok(true),
    ai_status: () => ok({ has_key: false, masked: "", translator: "auto", free_email: "" }),
    set_translator: () => ok(true),
    ai_set_key: () => ok({ has_key: true, model: "Claude Opus 5.5" }),
    ai_generate: (brief, cat, attrs, cur, pay, en) => ok({
      summary: "⚡ ChatGPT Plus — аренда личного аккаунта на 3 часа", desc: "✅ Что вы получаете:\n— личный аккаунт ChatGPT Plus\n— выдача сразу после оплаты\n\n💎 +1 час за отзыв",
      payment_msg: pay ? "Спасибо за покупку! Данные для входа — в этом чате." : "",
      summary_en: en ? "⚡ ChatGPT Plus — personal account rental for 3 hours" : undefined,
      desc_en: en ? "✅ What you get:\n— personal ChatGPT Plus account\n— instant delivery after payment\n\n💎 +1 hour for a review" : undefined,
      payment_msg_en: en && pay ? "Thanks for your purchase! Login details are in this chat." : undefined }),
    ai_translate: f => ok({ engine: "free", summary: f.summary ? "EN: " + f.summary : "", desc: f.desc ? "EN: " + f.desc : "", payment_msg: f.payment_msg ? "EN: " + f.payment_msg : "" }),
    update_progress: () => ok(0.5),
    install_update: () => new Promise(r => setTimeout(() => r({ ok: true, data: true }), 1500)),
    open_url: () => ok(true),
  };
})();

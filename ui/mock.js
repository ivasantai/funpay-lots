// Мок API для просмотра интерфейса в обычном браузере: ui/index.html?mock
(() => {
  const ok = data => new Promise(r => setTimeout(() => r({ ok: true, data }), 250));
  const cats = [
    { node: 1355, name: "Аккаунты ChatGPT", error: null, lots: [
      { id: 101, node: 1355, title: "ChatGPT Plus — аренда на 3 часа, личный аккаунт", server: "", amount: "1", price: "5", unit: "$", active: true },
      { id: 102, node: 1355, title: "ChatGPT Plus — аренда на 6 часов", server: "", amount: "1", price: "8", unit: "$", active: false },
    ]},
    { node: 1392, name: "Прочее Telegram", error: null, lots: [
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
  window.MOCK_API = {
    state: () => ok({ has_key: false, version: "mock" }),
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

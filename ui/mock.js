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
    login: () => ok({ id: 1, username: "DemoSeller", balance: "21 $" }),
    logout: () => ok(true),
    lots: () => ok(cats),
    games: () => ok([{ game: "ChatGPT", subs: [{ node: 1355, name: "Аккаунты" }, { node: 3559, name: "Подписка" }] },
                     { game: "Telegram", subs: [{ node: 1392, name: "Прочее" }] }]),
    form: (n, o) => ok(form(n, o)),
    save: () => ok({ done: true }),
    delete: () => ok({ done: true }),
    set_active: () => ok({ done: true }),
    forget_category: () => ok(true),
    open_url: () => ok(true),
  };
})();
